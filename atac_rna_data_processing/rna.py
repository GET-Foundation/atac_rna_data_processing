import os

import numpy as np
import pandas as pd
from pyranges import PyRanges as pr

from atac_rna_data_processing.gene import GeneExp
from atac_rna_data_processing.io.gencode import Gencode


def counts_to_log10tpm(counts):
    return np.log10(((counts / counts.sum(0))*1e6)+1)


def log10tpm_check(tpm):
    if (tpm.max() > 6) or (tpm.min() < 0):
        raise ValueError(
            "The gene expression is not in log10(TPM+1), you should figure out the correct transformation.")


class RNA(object):
    """Base class for RNA expression data."""

    def __init__(self, sample, assembly, version=40, transform=False, extend_bp=100):
        self.sample = sample
        self.assembly = assembly
        self.version = version
        self.transform = transform
        self.extend_bp = extend_bp
        self.rna = self.read_rna()
        self.tss, self.exp = self.get_data()
        self.export_data()

    def __repr__(self) -> str:
        return "RNA(sample={}, assembly={}, Gencode version=v{}, Max:{}, Mean: {}, Min:{})".format(self.sample, self.assembly, str(self.version), self.rna.TPM.max(), self.rna.TPM.mean(), self.rna.TPM.min())

    def read_rna(self):
        """Read the gene expression data."""
        if not os.path.exists(self.sample + ".promoter_exp.feather"):
            gencode = Gencode(assembly=self.assembly, version=self.version)
            gene_exp = pd.read_csv(self.sample + ".rna.csv", index_col=0)

            # if the gene expression is in log10(TPM+1), no transformation is needed
            if self.transform:
                gene_exp['TPM'] = counts_to_log10tpm(gene_exp.TPM.values)

            log10tpm_check(gene_exp.TPM.values)

            promoter_exp = pd.merge(gencode.gtf, gene_exp,
                                    left_on='gene_name', right_index=True)
            promoter_exp.reset_index().to_feather(self.sample + ".promoter_exp.feather")
        else:
            promoter_exp = pd.read_feather(
                self.sample + ".promoter_exp.feather")
            if (promoter_exp.TPM.max() > 6) or (promoter_exp.TPM.min() < 0):
                os.remove(self.sample + "promoter_exp.feather")
                raise ValueError(
                    "The gene expression is not in log10(TPM+1), you should figure out the correct transformation.")

        return promoter_exp.drop(['level_0', 'index'], axis=1, errors='ignore')

    def get_data(self):
        """Get the promoter expression data. Extend the promoter region by 100bp."""
        if os.path.exists(self.sample + ".exp.feather"):
            exp = pd.read_feather(self.sample + ".exp.feather")
        else:
            # open the ATAC-seq data
            atac = pr(pd.read_csv(self.sample + ".csv", index_col=0).reset_index())
            # join the ATAC-seq data with the RNA-seq data
            exp = atac.join(pr(self.rna).extend(self.extend_bp), how='left').as_df()
            # save the data to feather file
            exp.reset_index(drop=True).to_feather(self.sample + ".exp.feather")

        # group the data by the strand and calculate the mean
        exp = exp[['index', 'Strand', 'TPM']
                        ].groupby(['index', 'Strand']).mean().reset_index()
        # reset the index


        # get the negative strand expression data
        exp_n = exp[exp.Strand == "-"].iloc[:, 2].fillna(0)
        # set negative values to 0
        exp_n[exp_n < 0] = 0
        # get the positive strand expression data
        exp_p = exp[exp.Strand == "+"].iloc[:, 2].fillna(0)
        # set negative values to 0
        exp_p[exp_p < 0] = 0
        # get the negative strand TSS markers
        exp_n_tss = (exp[exp.Strand == "-"].iloc[:, 2] >= 0).fillna(False)
        # get the positive strand TSS markers
        exp_p_tss = (exp[exp.Strand == "+"].iloc[:, 2] >= 0).fillna(False)
        # stack the TSS data
        tss = np.stack([exp_p_tss, exp_n_tss]).T
        # stack the expression data
        exp = np.stack([exp_p, exp_n]).T
        return tss, exp

    def export_data(self):
        """Export the promoter expression data."""
        np.save(self.sample + ".exp.npy", self.exp)
        np.save(self.sample + ".tss.npy", self.tss)
    
    def get_gene(self, gene):
        """Get the expression data of a gene"""
        tss_list = self.rna[self.rna.gene_name == gene]
        id = tss_list.gene_id.values[0]
        chrom = tss_list.Chromosome.values[0]
        strand = tss_list.Strand.values[0]
        exp_list = tss_list.TPM.values
        tss_list = pr(tss_list)
        return GeneExp(gene, id, chrom, strand, tss_list, exp_list)

    def get_tss_atac_idx(self, chrom, tss):
        """Get the neighbor region of a given region"""
        exp = pd.read_feather(self.sample + ".exp.feather")
        tss_index_in_atac = exp[(exp.Chromosome == chrom) & (exp.Start_b+self.extend_bp==tss)].index.values
        return tss_index_in_atac
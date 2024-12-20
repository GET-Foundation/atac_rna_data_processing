# %%
from numpy import dtype, save
from atac_rna_data_processing.io.region import *
from atac_rna_data_processing.io.atac import read_bed4
#%%
hg38 = Genome('hg38', 'hg38.fa')
#%%
atac = read_bed4("test.atac.bed").as_df().head(100000)
#%%
atac = GenomicRegionCollection(hg38, atac)
#%%
seq = atac.center_expand(400).collect_sequence()
# %%
seq.save_npz("test_sequence")
# %%
from scipy.sparse import load_npz
load_npz("test_sequence_400.npz")

# %%
hg38.chrom_sizes
# %%
hg38.get_sequence("chr21", 0, hg38.chrom_sizes["chr21"])
# %%
import zarr
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import zarr

# {
#     "chunks": [
#         2000000
#     ],
#     "compressor": {
#         "blocksize": 0,
#         "clevel": 5,
#         "cname": "zstd",
#         "id": "blosc",
#         "shuffle": 2
#     },
#     "dtype": "<U1",
#     "fill_value": "",
#     "filters": null,
#     "order": "C",
#     "shape": [
#         248956422
#     ],
#     "zarr_format": 2
# }

def save_zarr_worker(self, zarr_file_path, chr, chrom_sizes):
    zarr_file = zarr.open_group(zarr_file_path, mode='a')  # open in append mode
    data = self.genome_seq.get_seq(chr, 1, chrom_sizes[chr]).seq.lower()
    # save string as list of characters
    data = list(data)
    zarr_file.create_dataset(chr, data=data, chunks=2000000, shape=len(data),
                             dtype='<U1', compressor=zarr.Blosc(cname='zstd', clevel=5, shuffle=2))
    return data

def save_zarr(self, zarr_file_path, 
              included_chromosomes=['chr1', 'chr2', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7',
                                    'chr8', 'chr9', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14',
                                    'chr15', 'chr16', 'chr17', 'chr18', 'chr19', 'chr20', 'chr21',
                                    'chr22', 'chrX', 'chrY']):
    """
    Save the genome sequence data in Zarr format using ThreadPoolExecutor.
    
    Args:
        zarr_file_path (str): Path to the Zarr file containing genome data.
        included_chromosomes (list): List of chromosomes to be included in the Zarr file.
    """
    zarr_file = zarr.open_group(zarr_file_path, 'a')  # Create the zarr file

    # Using ThreadPoolExecutor to manage a pool of threads
    with ThreadPoolExecutor() as executor:
        for chr in included_chromosomes:
            if os.path.exists(zarr_file_path):
                # If the Zarr file already exists, check if the chromosome is already saved
                if chr in zarr_file:
                    print(f"Chromosome {chr} already exists in the Zarr file.")
                    continue
            executor.submit(save_zarr_worker, self, zarr_file_path, chr, self.chrom_sizes)

    return
# %%
save_zarr(hg38, "hg38.zarr")
# %%
mm10 = Genome('mm10', '/home/xf2217/Projects/common/mm10/bigZips/mm10.fa')
# %%
save_zarr(mm10, "/home/xf2217/Projects/get_data/mm10_zstd.zarr/chrs", 
               included_chromosomes=[c for c in mm10.chrom_sizes.keys() if len(c) < 6])
# %%
seq= save_zarr_worker(mm10, "/home/xf2217/Projects/get_data/mm10_zstd.zarr/chrs", "chr1", mm10.chrom_sizes)

#%%
np.unique(mm10.genome_seq.get_seq('chr1', 15100000, 15200000).seq)
# %%

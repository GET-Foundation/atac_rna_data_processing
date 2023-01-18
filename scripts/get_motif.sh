#!/bin/bash
# Sample prefix name, e.g. test

SAMPLE=$1

# Set assembly with default hg38

ASSEMBLY=${2:-hg38}

# set memory and cpu with defaults

MEM=${3:-10G}
CPU=${4:-1}

# print usage with options

if [ $# -lt 2 ]; then
echo "Usage: $0 <sample> <assembly>"
echo "Assembly options: hg38 or mm10"
exit 1
fi

# Using tabix to extract the archetype motifs in atac peak regions for the given assembly
# if ${SAMPLE}.atac.motif.bed not exist:
if [ ! -f ${SAMPLE}.atac.motif.bed ]; then
    tabix -T ${SAMPLE}.atac.bed https://resources.altius.org/~jvierstra/projects/motif-clustering/releases/v1.0/${ASSEMBLY}.archetype_motifs.v1.0.bed.gz > ${SAMPLE}.atac.motif.bed
fi

# Using awk to extract the chromosome and motif information from the bed file

awk -v SAMPLE=${SAMPLE} '{OFS="\t"; print $1,$2,$3 > SAMPLE".atac."$1}' ${SAMPLE}.atac.bed
awk -v SAMPLE=${SAMPLE} '{print > SAMPLE".atac.motif."$1}' ${SAMPLE}.atac.motif.bed

# Using parallel to run the get_motif.per_chr.sh script in parallel using the specified memory and CPU

ls ${SAMPLE}.atac.motif.chr* | sed 's/.*motif.//' | parallel --memfree ${MEM} -j ${CPU} bash get_motif.per_chr.sh {} $SAMPLE

# Using xargs and sort to concatenate all the peak motif files into one bed file

ls ${SAMPLE}.atac.peak_motif* | sort -k1,1V | xargs cat > ${SAMPLE}.peak_motif.bed
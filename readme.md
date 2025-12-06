A streamlit database made for the purposes of walking a person through a few of the first steps for the actual code package. This is a mock, designed to show principles, so many mathmatical operations (such as finding the spearman correlation of two ptms), are replaced with similar ones for the sake of having a reasonable runtime. 

Tutorial: 
-IF YOU ENCOUNTER ERRORS, sqlalchemy is really bad with functions like adding columns so, if the columns get messed up it will throw errors. To fix drop everything and regenerate the dataset (run everyhting up until --gene_cccn_edges) using the commands found here: https://docs.google.com/document/d/1MwKjUs9-0x2uc3CU7pRgSiQOoIZFy-gew56n8cbKEtM/edit?usp=sharing. 

-Input Data:
The user must add the names of PTMs and drugs, these will be used to create the rest of the data. This is where the full CRUD interface is implamented. 

-ptmdataset: 
Based on the input data, a dataset will be created such that every ptm reacts with every drug. A (randomized) reaction score will be generated for you for every ptm-drug pair. 

-ptmcorrelationmatrix:
A matrix of ptm pairs will be created, each pair of ptms will have an "correlation score" from 0 to 1. The correlation score is based on how similar the two values react with a drug (i.e. even if they both barely react at all, you get a score of 1). 1 being evidence that two ptms are very strongly correlated and 0 resulting in no evidence. Since the original process (spearman correlation) takes a *very* long time to complete, I have created a mock algorithm to imitate it:

  cor_val = 0
  value for ptm1 is ptm1
  value_for_ptm2 is ptm2
  for drugs in row_of_ptmtable:
    cor_val += (val1 * val2) / max(val1, val2)^2
    
The correlation value of two ptms is the sum divided by the square max of the two values. In this case, if the two numbers are the same, then this will result in 1. Otherwise, the greater the difference between the two numbers, the less the total value will be. 

-clustering
Any ptm whose score is .5 or greater with another ptm will be put into a cluster with it. 
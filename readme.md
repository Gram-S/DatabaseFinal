This project has ended up focusing a little more on using SQL as an intermediate step for storing/querying data and having python analyze it. In the original project, every data structure is dependant on another, so it is difficult to justify implamenting a CRUD format into all of them. Instead, I only implamented a CRUD format into the "input data" section, so users can upload their data and have python analyze it to create the other data structures. It is my hope that this allows a user to understand the original project a little better. Additionally, while I do use some fairly advanced aggretition (mainly for finding the sums of reaction_scores) in sql, the main complexity comes from using python to analyze a sql database. 

P2Ppipeline(key).png is a figure that shows the full data structure flow for the original project, as well as gives some examples for the source data structures that I attempted to imitate in this project. The 2 data structures meant to be shown in this project is the original dataset (called ptmtable in the figure, ptmdataset in this project) and the correlation matrix (ptm.correlation.matrix in figure, ptmcorrelationmatrix in project). Also included is a list of PTM and drug names in case the user wants their data to be realistic (datalist.txt). 

-Explanation: 
A Post-Translational Modification (PTM) takes place inside cells after they create a protein. It is the modification of that protein that occurs after it is folded (as opposed to being modified during its creation or folding), such as lipoylation, the attachment of a C8 molecule to a protein (PTMs wikipedia). PTMs are more abstract than something physical like a cell, so instead, we look at how cells respond to some enviromental condition (called a drug in this project for simplicity) and measure if number of times the PTM is performed increases. Our goal is to find which PTMs have a similar reaction score, as we conclude that in response to a drug, which PTMs will or will not be performed. This gives us a better insight into how a drug modifies a persons proteome (ALL of the proteins in their body). We denote PTMs with similar reaction scores as "clustering" together. 

Note: You may be wondering why our final output isn't something like (drug -> causes: ptm1, ptm3, ptm5). The reason for this is because of the, quite frankly, insane difficulty (at least for me) it comes to understanding the biological reasoning that goes into this, and this project is designed to mock the functionality of the original. This gives us a better insight into how a drug modifies a persons proteome (ALL of the proteins in their body). We denote PTMs with similar reaction scores as "clustering" together. 

-Input Data:
To do this, The user must make up the names of PTMs and drugs using a full CRUD interface. Note the full CRUD interface is only on the input data page as every other data table will be changed if the input data is changed. 

-ptmdataset: 
We will pretend like we measured a reaction score for every possible PTM x drug pair, but it is just assigned randomly. In the real world, this is mainly done through the use of mass spectrometry, which I neither have the knowledge nor the funds to reproduce solely using SQL and python. 

-ptmcorrelationmatrix:
Now we want to find which pairs of PTMs share a similar reaction score. We do this by calculating the "spearman_score" which tells us how close the reaction score of PTM1 is to PTM2 on a scale of 0 to 1 (1 being the same number, the closer to 0 the larger difference between the numbers). Due to the high time and computation requirements of an actual spearman correlation function, I instead used:

  Let r1 and r2 be a reaction score for ptm1 and ptm2 respectively
  Then the spearman score between ptm1 and ptm2 is: min(r1, r2) / max(r1, r2)
  
This function has no mathmatical significance, but it perserves 2 traits from the dataset that would be created in the source material other than the bounds (0 to 1) and distance traits (bigger distance = smaller) as stated above.
- A ptm pair that contains 2 of the same ptm has a score of 1.
- PTM1 and PTM2 have the same spearman score as PTM2 and PTM1 (order doesn't matter). This is because they originally come from a symmetrical matrix (can be viewed on the P2Ppipeline(key).png figure). 

-common_clusters
Now, we say a pair of PTMs clusters with another if one of its spearman scores is similar to the spearman_score of another. I set my cutoff at 0.5, so only spearman_scores with a difference of 0.5 or less from eachother will cluster. We then say that the PTMs in that cluster react to enviromental conditions in a similar way, please note that conclusion is not accurate to the original project since I am choosing not to include techniques for analyizing clusters in this projects, but I wanted to have some interesting "final" data output. 

Also please note that you very commonly only output 1 cluster due to the small sample size and some weirdness with the uniform randomness used in the process of creating the spearman_score. 
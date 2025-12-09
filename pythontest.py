import pandas as pd 

one = [1,2,3,4,5,6]
two = ["a",'b','c','d', 'e', 'f']

df = pd.DataFrame([one,two])
print(df)
print(df.iloc[0, 1])
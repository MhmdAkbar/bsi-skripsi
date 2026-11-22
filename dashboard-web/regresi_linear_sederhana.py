import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

X = sm.add_constant(df['nss'])
model = sm.OLS(df['dea'], X).fit()
dw = durbin_watson(model.resid)
print(dw)
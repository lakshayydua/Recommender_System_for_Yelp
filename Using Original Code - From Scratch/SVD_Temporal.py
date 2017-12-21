import pandas as pd
import numpy as np
from scipy import sparse
from datetime import datetime
from sklearn.model_selection import train_test_split


# ================= FUNCTIONS ==================
# predict initial bias
def predictBaseRating(user, business):
    return mu + bu[user] + bi[business]


# def findNewRating(user, business):
#    return np.dot(Qi[business], Pu[user])

#This function is used for predicting the rating for the next iteration in order to check if the factor update is required using Stochastic Gradient Descent Technique and also for predicting the rating for the test data.
def findNewRating(user, business):
    try:
        rat = np.dot(Qi[business], Pu[user])+bi[business]+bu[user]+mu+Item[connect[user,business],business]
        if rat > 5:
            return 5
        elif rat < 1:
            return 1
        else:
            return rat
    except:
        return mu


# ===== calculates RMSE =====
def calculateRMSE():
    sumSqErr = 0
    count = 0
    for u, i, r in zip(urM.row, urM.col, urM.data):
        err = r - findNewRating(u, i)
        sumSqErr = sumSqErr + err * err
        count = count + 1

    meanSqErr = sumSqErr / count
    rmse = np.sqrt(meanSqErr)

    return rmse


# load data from file
rawData = pd.read_csv('/home/askapoor/Downloads/train_rating.txt', sep=",",
                      dtype={"train_id": np.int32, "user_id": np.int32, "business_id": np.int32, "rating": np.int8,
                             "date": str})
rawDataTrain, testData = train_test_split(rawData, test_size=0.3, random_state=42)

# determine the dimension of the data
numOfRow = rawData.shape[0]
numOfCol = rawData.shape[1]

#For grouping the training data for Item Temporal Analysis
train_df = rawData
test = train_df
test.loc[:,'date'] = pd.to_datetime(test['date'])
test = test[['business_id','rating','date']]
test.loc[:,'date'] = test.loc[:,'date'].dt.year
test = test.groupby(['business_id','date'],as_index = False).agg(['mean']).reset_index()
test.columns = test.columns.droplevel(1)

#ItemTemporal bias sparse matrix
businessId_t = test['business_id'].values
date_t = test['date'].values
test.loc[:,'year_bias'] = 0
Itemyearbias = sparse.coo_matrix((test.loc[:,'year_bias'].values, (date_t, businessId_t)))


train_df.loc[:,'date'] = pd.to_datetime(train_df.loc[:,'date'])
train_df.loc[:,'date'] = train_df.loc[:,'date'].dt.year
train_df = train_df[['user_id','business_id','date']]


#Sparse matrix for connecting year to ItemTemporal Bias matrix
userId_u = train_df['user_id'].values
businessId_u = train_df['business_id'].values
date_u = train_df['date'].values
connection = sparse.coo_matrix((date_u, (userId_u, businessId_u)))

userId = rawData['user_id'].values
businessId = rawData['business_id'].values
rating = rawData['rating'].values
userRating = sparse.coo_matrix((rating, (userId, businessId)))

# calculate average rating throughout whole dataset
mu = np.average(rating)

# determine average movie rating
# determine average user rating
(x, y, z) = sparse.find(userRating)
countUser = np.bincount(x)
print(countUser)
CountBusiness = np.bincount(y)
sumsUser = np.bincount(x, weights=z)
sumsBusiness = np.bincount(y, weights=z)
averageUserRating = sumsUser / countUser
averageBusinessRating = sumsBusiness / CountBusiness
#Initializing  biases depending upon the training values and this just for checking and for assessing the shape. These parameter will again be initialize and learned through Stochastic Gradient Descent.
bu = averageUserRating - mu
bi = averageBusinessRating - mu
print(bi.shape,bu.shape)
print('mu',mu)

# ==================== LEARNING: DETERMINE Qi, Pu, bi, bu (Initializing these parameters)=====================
# declare initial Qi and Pu
N = 200  # common dimension of Qi, Pu
seedVal = np.sqrt(mu / N)
ni = bi.shape[0]
nu = bu.shape[0]
# Qi = np.array([[seedVal/N] * N] * ni)
# Pu = np.array([[seedVal/N] * N] * nu)
# Qi = np.random.rand(ni,N)
# Pu = np.random.rand(nu,N)
Qi = np.random.normal(scale=1/200,size=(ni,N))
Pu = np.random.normal(scale=1/200,size=(nu,N))
bi = np.zeros(145303,np.double)
bu = np.zeros(693209,np.double)
#print(Qi.shape)
# ------------ calculate Qi,Pu,bi, bu and item temporal bias through iteration----------------
urM = sparse.coo_matrix(userRating)
lrate = .012  # learning rate
lamb = .15
iteratioN = 15
rmseIte = [0] * (iteratioN + 1)
tol = .00001
Item = Itemyearbias.tocsr()
connect = connection.tocsr()
for ite in range(iteratioN):
    for u, i, r in zip(urM.row, urM.col, urM.data):
        rat = np.dot(Qi[i], Pu[u])+bi[i]+bu[u]+mu+Item[connect[u,i],i]
        #print(rat)
        if rat > 5:
            rat = 5
        elif rat < 1:
            rat = 1
        err = r - rat
        Qi[i] = Qi[i] + lrate * (err * Pu[u] - lamb * Qi[i])
        Pu[u] = Pu[u] + lrate * (err * Qi[i] - lamb * Pu[u])
        bi[i] = bi[i]+ lrate * (err - lamb * bi[i])
        bu[u] = bu[u] + lrate * (err - lamb * bu[u])
        Item[connect[u, i], i] = Item[connect[u, i], i] + lrate * (err - lamb * Item[connect[u, i], i])
    # check RMSE for breaking condition
    rmseIte[ite + 1] = calculateRMSE()
    print('RMSE-' + str(ite + 1) + ' = ' + str(rmseIte[ite + 1]))
    if (np.abs(rmseIte[ite + 1] - rmseIte[ite]) < tol):
        break

# ==================== GENERATE TEST RESULT ======================
# load test file
# load data from file
testData = pd.read_csv('/home/askapoor/Downloads/test_rating.txt', sep=",",
                       dtype={"test_id": np.int32, "user_id": np.int32, "business_id": np.int32, "date": str})
testData['rating'] = 0

for index, row in testData.iterrows():
    user = testData.loc[index, 'user_id']
    business = testData.loc[index, 'business_id']
    ratingUI = findNewRating(user, business)
    testData.loc[index, 'rating'] = ratingUI

# round and ceil if >5 or <1
testData.loc[testData.rating < 1, 'rating'] = 1
testData.loc[testData.rating > 5, 'rating'] = 5

# write to csv file
testFilename = '/home/askapoor/Downloads/test_stochastic_N_' + str(N) + '_iter_' + str(iteratioN) + '_lambda_' + str(
    lamb) + '_lrate_' + str(lrate) + '_' + str(datetime.now()).replace(':', '-').replace(' ', '_')[:19] + '.csv'
testData.to_csv(testFilename, sep=',', columns=['test_id', 'rating'], header=True, index=False, mode='w')


# -*- coding: utf-8 -*-
"""Copy of DL_Assign2_Ques2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JlJE9SzLLyrxcpKiLHWeeYsER-pmUeKQ
"""

import subprocess
import os
from matplotlib import pyplot as plt
url = 'https://archive.ics.uci.edu/ml/machine-learning-databases/00235/household_power_consumption.zip'
!mkdir data
!wget {url} -O household_power_consumption.zip
!unzip household_power_consumption.zip -d /content/data


os.remove('household_power_consumption.zip')

!pip3 -q install torchmetrics

!pip3 -q install torchinfo

# pytorch libs
import torch
from torch import nn
import torchvision
import matplotlib.pyplot as plt
import numpy as np
import torchmetrics
import torchmetrics
from torchmetrics.classification import Accuracy
import torchinfo
from torchinfo import summary

device = "cuda" if torch.cuda.is_available() else "cpu"
device

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Load the dataset
datafr = pd.read_csv('/content/data/household_power_consumption.txt', delimiter=';', 
                 parse_dates={'datetime': ['Date', 'Time']}, infer_datetime_format=True, 
                 na_values=['?', 'NaN'], index_col='datetime')
datafr.dropna(inplace=True)
new_df = datafr.drop(['Global_active_power'], axis=1)
labels = datafr['Global_active_power']
cols = datafr.columns
#  Train:Test (80:20)
X_train, X_test, y_train, y_test = train_test_split(new_df, labels, test_size=0.2, random_state=42)

datafr.head()

X_train.head()

# Basic preprocessing - convert object columns to numeric
X_train['Sub_metering_1'] = pd.to_numeric(X_train['Sub_metering_1'])
X_train['Sub_metering_2'] = pd.to_numeric(X_train['Sub_metering_2'])
X_train['Sub_metering_3'] = pd.to_numeric(X_train['Sub_metering_3'])

X_test['Sub_metering_1'] = pd.to_numeric(X_test['Sub_metering_1'])
X_test['Sub_metering_2'] = pd.to_numeric(X_test['Sub_metering_2'])
X_test['Sub_metering_3'] = pd.to_numeric(X_test['Sub_metering_3'])

X_train.head()

# preprocessing the data with robust scaler
y_train = y_train.values.reshape(-1,1)
y_test = y_test.values.reshape(-1,1)
from sklearn.preprocessing import RobustScaler
sc_x_var = RobustScaler()
sc_y_var = RobustScaler()
X_train = sc_x_var.fit_transform(X_train)
y_train = sc_y_var.fit_transform(y_train)
X_test = sc_x_var.transform(X_test)
y_test = sc_y_var.transform(y_test)
# convert the scaled data into dataframe
datafr_train = pd.DataFrame(X_train, columns=cols[1:])
datafr_train['Global_active_power'] = y_train
datafr_train.head()

datafr_test = pd.DataFrame(X_test, columns=cols[1:])
datafr_test['Global_active_power'] = y_test
datafr_test.head()

import torch
from torch.utils.data import Dataset

class SequenceDataset(Dataset):
    def __init__(self, dataframe, target, features, sequence_length=5):
        self.features = features
        self.target = target
        self.sequence_length = sequence_length
        self.y = torch.tensor(dataframe[target].values).float()
        self.X = torch.tensor(dataframe[features].values).float()

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, i): 
        if i >= self.sequence_length - 1:
            i_start = i - self.sequence_length + 1
            x = self.X[i_start:(i + 1), :]
        else:
            padding = self.X[0].repeat(self.sequence_length - i - 1, 1)
            x = self.X[0:(i + 1), :]
            x = torch.cat((padding, x), 0)

        return x, self.y[i]

sequence_length = 25
features = cols[1:]
target = cols[0]

print(f"features: {features}")
print(f"target: {target}")

# create train dataset
train_dataset = SequenceDataset(dataframe=datafr_train,target=target,features=features,sequence_length=sequence_length)

# create test dataset
test_dataset = SequenceDataset(dataframe=datafr_test,target=target,features=features,sequence_length=sequence_length)

from torch.utils.data import DataLoader

batch = 256

train_iterator = DataLoader(train_dataset, batch_size=batch, shuffle=True)
test_iterator = DataLoader(test_dataset, batch_size=batch)

X_sample, y_sample = next(iter(train_iterator))
# print(f"Train X_sample: {X_sample}")
print(f"Train x_sample shape: {X_sample.shape}")
print(f"length of train dataloader: {len(train_iterator)}")
print(f"length of test dataloader: {len(test_iterator)}")

def plot_graph(y_predicted,y_real):
    plt.figure(figsize=(12, 6))
    plt.plot(y_real, label='Real')
    # plt.plot(y_real, label='Y-Predicted20')
    # plt.plot(y_predicted, label='Y-Predicted30')
    plt.plot(y_predicted, label='Predicted')
    plt.xlabel('Time')
    plt.ylabel('Global Active Power')
    plt.legend()
    plt.show()
def plot_loss(out_dict):
    loss = out_dict["Train_Loss"]
    test_loss = out_dict["Test_Loss"]
    epochs = range(len(out_dict["Train_Loss"]))
    plt.figure(figsize=(15, 7))
    plt.subplot(1, 2, 1)
    plt.plot(epochs, loss, label="Train_Loss", color='blue')
    plt.plot(epochs, test_loss, label="Test_Loss", color='purple')
    plt.title("Loss")
    plt.xlabel("Epochs")
    plt.legend()

def train_model(model,dataloader,loss_fn,optimizer,device):

    model.train() 
    train_loss = 0 
    for (X, y) in dataloader: 
        y = y.type(torch.float32)
        X, y = X.to(device), y.to(device)
        # print(f"shape of X: {X.shape}, shape of y: {y.shape}")
        y_pred_logits = model(X)
          # n_correct += 1 if y_pred_temp<0.5 else 0
        # print(f"type of y_pred_logits: {y_pred_logits.dtype}, type of y: {y.dtype}")
        loss = loss_fn(y_pred_logits, y)
        train_loss += loss.item()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return train_loss / len(dataloader)
# pred_values=np.zeros(y_test.shape)
y_pred20 = []
y_real20 = []
# y_pred30 = []
# y_real30 = []
def test_model(model,dataloader,loss_fn,device):
    model.eval()  # putting model in eval model
    test_loss = 0  # initlizing loss 
    n_samples = 0
    n_correct = 0
    with torch.inference_mode(): # disabling inference mode for aqcuiring gradients of perturbed data
      for i, (X, y) in enumerate(dataloader):  # loop in batches
          X, y = X.to(device), y.to(device)  # sending the data to target device
          # print(f"shape of X: {X.shape}, shape of y: {y.shape}")

          # 1. forward pass
          y_pred_logits = model(X)

          # 2. calculate the loss
          loss = loss_fn(y_pred_logits, y)
          
          test_loss += loss.item()
          y_pred_temp=torch.abs(y_pred_logits-y)
          n_samples += y.size(0)
          n_correct += (y_pred_temp <0.04).float().sum().item()
          # print(n_correct)
          # print(type(y_pred_temp.item()))
          # n_correct += 1 if y_pred_temp<0.5 else 0
          y_pred20.extend(y_pred_logits.tolist())
          y_real20.append(y)
          # y_pred30.extend(y_pred_logits.tolist())
          # y_real30.append(y)
      acc = 100.0 * n_correct / n_samples
      # print(f'Accuracy of the network: {acc} %')
    # 6. returning actual loss and acc.
    return test_loss / len(dataloader), acc
from tqdm.auto import tqdm
def train(model: nn.Module,train_dataloader: torch.utils.data.DataLoader,test_dataloader: torch.utils.data.DataLoader,loss_fn: nn.Module,optimizer: torch.optim.Optimizer,epochs: int):
    out_dict = {"Train_Loss": [], "Test_Loss": [], "Test_Acc": []}
    for epoch in tqdm(range(epochs)):
        train_loss = train_model(model=model,dataloader=train_dataloader,loss_fn=loss_fn,optimizer=optimizer,device=device,)
        test_loss,accuracy = test_model(model=model,dataloader=test_dataloader,loss_fn=loss_fn,device=device,)
        print(
            f"Epoch: {epoch+1} | "
            f"Train_Loss: {train_loss:.4f} | "
            f"Test_Loss: {test_loss:.4f} | "
            f"Test_Acc: {accuracy:.4f}"
        )
        out_dict["Train_Loss"].append(train_loss)
        out_dict["Test_Loss"].append(test_loss)
        out_dict["Test_Acc"].append(accuracy)
    return out_dict

from torch import nn
class LSTMModel(nn.Module):
    def __init__(self, num_features, hidden_units):
        super().__init__()
        self.num_features = num_features
        self.hidden_units = hidden_units
        self.num_layers = 1
        self.lstm = nn.LSTM(input_size=num_features,hidden_size=hidden_units,batch_first=True,num_layers=self.num_layers)
        self.linear = nn.Linear(in_features=self.hidden_units, out_features=1)

    def forward(self, x):
        batch_size = x.shape[0]
        hidden = torch.zeros(self.num_layers, batch_size, self.hidden_units).requires_grad_().to(device=device)
        cell = torch.zeros(self.num_layers, batch_size, self.hidden_units).requires_grad_().to(device=device)
        _, (hn, _) = self.lstm(x, (hidden, cell))
        out = self.linear(hn[0]).flatten()  # First dim of Hn is num_layers, which is set to 1 above.

        return out

model20 = LSTMModel(num_features=6, hidden_units=256).to(device)
epochs = 10
#Using L1 Loss function
criterion = nn.L1Loss()
optimizer = torch.optim.Adam(model20.parameters(), lr=0.001)

# test_loss = testing_step(
#             model=model0,
#             dataloader=test_dataloader,
#             loss_fn=loss_fn,
#             device=device,
#         )

model20_output = train(model=model20,train_dataloader=train_iterator,test_dataloader=test_iterator,optimizer=optimizer,loss_fn=criterion,epochs=epochs)
plot_loss(model20_output)

# print(y_pred30[3])
plot_graph(y_pred20,y_real20)



X_train, X_test, y_train, y_test = train_test_split(new_df, labels, test_size=0.3, random_state=42)

# Basic preprocessing - convert object columns to numeric
X_train['Sub_metering_1'] = pd.to_numeric(X_train['Sub_metering_1'])
X_train['Sub_metering_2'] = pd.to_numeric(X_train['Sub_metering_2'])
X_train['Sub_metering_3'] = pd.to_numeric(X_train['Sub_metering_3'])

X_test['Sub_metering_1'] = pd.to_numeric(X_test['Sub_metering_1'])
X_test['Sub_metering_2'] = pd.to_numeric(X_test['Sub_metering_2'])
X_test['Sub_metering_3'] = pd.to_numeric(X_test['Sub_metering_3'])

# preprocessing the data with robust scaler
y_train = y_train.values.reshape(-1,1)
y_test = y_test.values.reshape(-1,1)
from sklearn.preprocessing import RobustScaler
sc_x_var = RobustScaler()
sc_y_var = RobustScaler()
X_train = sc_x_var.fit_transform(X_train)
y_train = sc_y_var.fit_transform(y_train)
X_test = sc_x_var.transform(X_test)
y_test = sc_y_var.transform(y_test)
# convert the scaled data into dataframe
datafr_train = pd.DataFrame(X_train, columns=cols[1:])
datafr_train['Global_active_power'] = y_train
datafr_train.head()

datafr_test = pd.DataFrame(X_test, columns=cols[1:])
datafr_test['Global_active_power'] = y_test
datafr_test.head()

sequence_length = 25
features = cols[1:]
target = cols[0]

print(f"features: {features}")
print(f"target: {target}")

# create train dataset
train_dataset = SequenceDataset(dataframe=datafr_train,target=target,features=features,sequence_length=sequence_length)

# create test dataset
test_dataset = SequenceDataset(dataframe=datafr_test,target=target,features=features,sequence_length=sequence_length)

from torch.utils.data import DataLoader

batch = 256

train_dataloader = DataLoader(train_dataset, batch_size=batch, shuffle=True)
test_dataloader = DataLoader(test_dataset, batch_size=batch)

X_sample, y_sample = next(iter(train_dataloader))
# print(f"Train X_sample: {X_sample}")
print(f"Train x_sample shape: {X_sample.shape}")
print(f"length of train dataloader: {len(train_dataloader)}")
print(f"length of test dataloader: {len(test_dataloader)}")

model30 = LSTMModel(num_features=6, hidden_units=256).to(device)
epochs = 10
#Using L1 Loss function
criterion = nn.L1Loss()
optimizer = torch.optim.Adam(model30.parameters(), lr=0.001)

model20_output = train(model=model20,train_dataloader=train_dataloader,test_dataloader=test_dataloader,optimizer=optimizer,loss_fn=criterion,epochs=epochs)
plot_loss(model20_output)

# test_loss,accuracy = test_model(
#             model=model3,
#             dataloader=test_dataloader,
#             loss_fn=loss_fn,
#             device=device,
#         )

# print(y_pred30[3])
plot_graph(y_pred30,y_real30)

# print(y_pred30[3])
plot_graph(y_pred20,y_pred30)


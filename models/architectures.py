"""Definición canónica de las arquitecturas de redes neuronales PyTorch.

Implementa los modelos de la tesis de la UPEC:
  1. CNN_LSTM: Red neuronal híbrida (Etapa 2 de la cascada)
  2. Autoencoder: Red de reconstrucción para detección de anomalías (Etapa 3)
"""

import torch
import torch.nn as nn


class CNN_LSTM_PyTorch(nn.Module):
    def __init__(self, n_features, n_classes=1):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.pool1 = nn.MaxPool1d(2)
        
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(2)
        
        # Secuencia espacial extraída por la CNN modelada por LSTM
        self.lstm = nn.LSTM(input_size=128, hidden_size=64, batch_first=True)
        self.dropout = nn.Dropout(0.3)
        self.fc1 = nn.Linear(64, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, n_classes)
        self.act = nn.Sigmoid() if n_classes == 1 else nn.Softmax(dim=1)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        elif x.dim() == 3 and x.size(2) == 1:
            x = x.transpose(1, 2)
            
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.pool1(x)
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.pool2(x)
        
        x = x.permute(0, 2, 1)
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]
        x = self.dropout(last_step)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return self.act(x)


class Autoencoder_PyTorch(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(n_features, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, n_features),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

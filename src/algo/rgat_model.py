"""
src/algo/rgat_model.py

RGAT thực sự: mỗi loại quan hệ có weight riêng.
Dùng RGATConv từ torch_geometric thay vì GATConv thông thường.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import RGATConv


# Danh sách loại quan hệ trong DocVQA graph
RELATION_TYPES = [
    "SEQUENTIAL",       # câu hỏi liên tiếp trong tài liệu
    "SAME_PAGE",        # cùng trang
    "SAME_SECTION",     # cùng section/block
    "VISUAL_NEAR",      # gần nhau về layout (bbox overlap)
]
NUM_RELATIONS = len(RELATION_TYPES)
REL2IDX = {r: i for i, r in enumerate(RELATION_TYPES)}


class RGAT(nn.Module):
    """
    2-layer RGAT encoder.

    Input:
        x          : [N, in_channels]  node features (BERT embeddings)
        edge_index : [2, E]            edges
        edge_type  : [E]               loai quan he (0..num_relations-1)

    Output:
        [N, out_channels]  node embeddings sau khi encode graph
    """

    def __init__(
        self,
        in_channels:    int = 768,
        hidden_channels: int = 256,
        out_channels:   int = 128,
        num_relations:  int = NUM_RELATIONS,
        heads:          int = 4,
        dropout:        float = 0.1,
    ) -> None:
        super().__init__()

        self.dropout = dropout

        # Lop 1: in_channels → hidden_channels (multi-head)
        self.rgat1 = RGATConv(
            in_channels=in_channels,
            out_channels=hidden_channels,
            num_relations=num_relations,
            heads=heads,
            concat=True,
            dropout=dropout,
        )

        # Lop 2: hidden_channels*heads → out_channels (single head)
        self.rgat2 = RGATConv(
            in_channels=hidden_channels * heads,
            out_channels=out_channels,
            num_relations=num_relations,
            heads=1,
            concat=False,
            dropout=dropout,
        )

        # Layer norm
        self.norm1 = nn.LayerNorm(hidden_channels * heads)
        self.norm2 = nn.LayerNorm(out_channels)

        # Projection dau vao neu in_channels != out_channels (cho residual)
        self.proj = (
            nn.Linear(in_channels, out_channels, bias=False)
            if in_channels != out_channels else nn.Identity()
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_type: torch.Tensor,
    ) -> torch.Tensor:

        # Handle empty graph
        if x.size(0) == 0:
            return x

        identity = self.proj(x)  # [N, out_channels] cho residual

        # Lop 1
        h = self.rgat1(x, edge_index, edge_type)
        h = self.norm1(h)
        h = F.elu(h)
        h = F.dropout(h, p=self.dropout, training=self.training)

        # Lop 2 + residual
        h = self.rgat2(h, edge_index, edge_type)
        h = self.norm2(h + identity)  # residual connection

        return h  # [N, out_channels]


class RGATWithClassifier(nn.Module):
    """
    RGAT + classifier dau ra.
    Dung cho training supervised: chon node nao la dap an.
    """

    def __init__(
        self,
        in_channels:    int = 768,
        hidden_channels: int = 256,
        out_channels:   int = 128,
        num_relations:  int = NUM_RELATIONS,
        num_classes:    int = 2,   # co phai dap an hay khong
    ) -> None:
        super().__init__()
        self.encoder = RGAT(in_channels, hidden_channels, out_channels, num_relations)
        self.classifier = nn.Sequential(
            nn.Linear(out_channels, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, num_classes),
        )

    def forward(self, x, edge_index, edge_type):
        h = self.encoder(x, edge_index, edge_type)
        return self.classifier(h)  # [N, num_classes]
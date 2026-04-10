#!/usr/bin/env python3
"""
Modal Interface — 새 모달 추가 시 코드 수정 없이 확장 가능한 인터페이스

사용법:
    from modal_interface import BaseModalEncoder, registry

    # 등록된 encoder 조회
    registry.list_modals()
    enc_cls = registry.get("crispr")

    # 새 모달 추가 (3단계)
    # 1) BaseModalEncoder 상속
    # 2) modal_name / input_dim / output_dim 정의
    # 3) registry.register()
    class MyEncoder(BaseModalEncoder):
        modal_name = "my_modal"
        input_dim = 256
        output_dim = 128
        def __init__(self, dropout=0.2):
            super().__init__(self.input_dim, self.output_dim, dropout)
            self.net = nn.Sequential(...)
        def forward(self, x): return self.net(x)
    registry.register("my_modal", MyEncoder)
"""

from abc import ABC, abstractmethod

import torch
import torch.nn as nn


# ═══════════════════════════════════════════════════════════════════
# 1. Abstract Base Encoder
# ═══════════════════════════════════════════════════════════════════

class BaseModalEncoder(ABC, nn.Module):
    """모든 모달 Encoder가 상속해야 하는 추상 클래스.

    서브클래스 필수:
      - modal_name (str) : 모달 고유 이름
      - input_dim  (int) : 입력 차원
      - output_dim (int) : 출력 임베딩 차원
      - forward(x)       : (B, input_dim) → (B, output_dim)
      - get_modal_name() : modal_name 반환
    """

    modal_name: str = ""
    input_dim: int = 0
    output_dim: int = 0

    def __init__(self, input_dim: int, output_dim: int, dropout: float = 0.2):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.dropout = dropout

    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(B, input_dim) → (B, output_dim)"""
        ...

    @classmethod
    def get_modal_name(cls) -> str:
        if not cls.modal_name:
            raise ValueError(f"{cls.__name__}.modal_name이 정의되지 않았습니다.")
        return cls.modal_name

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}"
                f"(modal={self.get_modal_name()}, "
                f"in={self.input_dim}, out={self.output_dim})")


# ═══════════════════════════════════════════════════════════════════
# 2. Modal Registry
# ═══════════════════════════════════════════════════════════════════

class ModalRegistry:
    """Encoder 등록/조회 레지스트리.

    사용법:
        registry.register("crispr", CRISPREncoder)
        enc_cls = registry.get("crispr")
        registry.list_modals()  # → [{name, class, input_dim, output_dim, status}]
    """

    def __init__(self):
        self._registry: dict[str, type[BaseModalEncoder]] = {}

    def register(self, name: str, encoder_cls: type[BaseModalEncoder]):
        """새 Encoder 클래스 등록."""
        if not issubclass(encoder_cls, BaseModalEncoder):
            raise TypeError(
                f"{encoder_cls.__name__}은 BaseModalEncoder를 상속해야 합니다."
            )
        self._registry[name] = encoder_cls

    def get(self, name: str) -> type[BaseModalEncoder]:
        """이름으로 Encoder 클래스 조회."""
        if name not in self._registry:
            available = ", ".join(sorted(self._registry.keys())) or "(없음)"
            raise KeyError(f"'{name}' 모달 미등록. 등록된 모달: {available}")
        return self._registry[name]

    def list_modals(self) -> list[dict]:
        """등록된 모달 목록 반환."""
        result = []
        for name, cls in sorted(self._registry.items()):
            result.append({
                "name": name,
                "class": cls.__name__,
                "input_dim": cls.input_dim,
                "output_dim": cls.output_dim,
                "status": "READY" if cls.input_dim > 0 else "TBD",
            })
        return result

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        return f"ModalRegistry({len(self)} modals: {list(self._registry.keys())})"


# Global registry — import 시 바로 사용 가능
registry = ModalRegistry()


# ═══════════════════════════════════════════════════════════════════
# 3. 기존 5개 Encoder (BaseModalEncoder 상속)
# ═══════════════════════════════════════════════════════════════════

class CRISPREncoder(BaseModalEncoder):
    """DepMap CRISPR gene dependency → 128-d embedding.

    입력: DepMap CRISPR knockout viability scores (18,310 genes)
    출처: DepMap Public 24Q2 (sample__crispr__*)
    """
    modal_name = "crispr"
    input_dim = 18310
    output_dim = 128

    def __init__(self, input_dim: int = 18310, output_dim: int = 128, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MorganFPEncoder(BaseModalEncoder):
    """Morgan fingerprint (2048-bit) → 128-d embedding.

    입력: RDKit Morgan FP radius=2, nBits=2048
    출처: ChEMBL SMILES → RDKit (drug_morgan_*)
    """
    modal_name = "morgan_fp"
    input_dim = 2048
    output_dim = 128

    def __init__(self, input_dim: int = 2048, output_dim: int = 128, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class LINCSEncoder(BaseModalEncoder):
    """LINCS L1000 similarity scores → 64-d embedding.

    입력: 약물-세포주 전사체 유사도 5개 feature
    출처: LINCS L1000 CMap (lincs_*)
    """
    modal_name = "lincs"
    input_dim = 5
    output_dim = 64

    def __init__(self, input_dim: int = 5, output_dim: int = 64, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)
        self.net = nn.Sequential(
            nn.Linear(input_dim, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TargetEncoder(BaseModalEncoder):
    """Drug-Target interaction → 64-d embedding.

    입력: 약물-타겟 상호작용 feature 10개
    출처: ChEMBL + UniProt (target_*)
    """
    modal_name = "target"
    input_dim = 10
    output_dim = 64

    def __init__(self, input_dim: int = 10, output_dim: int = 64, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)
        self.net = nn.Sequential(
            nn.Linear(input_dim, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DrugDescEncoder(BaseModalEncoder):
    """RDKit molecular descriptors → 64-d embedding.

    입력: 분자 물리화학 기술자 9개 (MolWt, LogP, TPSA, HBD, HBA, RotBonds, Rings, AromaticRings, FractionCSP3)
    출처: RDKit Descriptors (drug_desc_*)
    """
    modal_name = "drug_desc"
    input_dim = 9
    output_dim = 64

    def __init__(self, input_dim: int = 9, output_dim: int = 64, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)
        self.net = nn.Sequential(
            nn.Linear(input_dim, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ═══════════════════════════════════════════════════════════════════
# 4. 향후 추가 예정 모달 Stub
# ═══════════════════════════════════════════════════════════════════

# ── 4-1. 이미지 계열: MedicalImageEncoder (통합) ─────────────────
#
# image_type 파라미터로 이미지 종류를 구분하여 하나의 클래스로 재사용.
# 향후 image_type만 바꾸면 다른 영상에 바로 적용 가능.
#
# ┌──────────────┬──────────────────────────────────────────────────┐
# │ image_type   │ 설명                                            │
# ├──────────────┼──────────────────────────────────────────────────┤
# │ pathology    │ H&E 병리 슬라이드 → tile feature (ResNet/ViT)   │
# │ histology    │ IHC/특수염색 조직학 이미지                       │
# │ ct           │ CT 슬라이스 3D feature                           │
# │ xray         │ 흉부/유방 X-ray feature                         │
# └──────────────┴──────────────────────────────────────────────────┘
#
# 질환별 예상 사용 이미지 타입:
# ┌──────────────┬──────────────────────────────────────────────────┐
# │ 질환         │ 주요 image_type                                 │
# ├──────────────┼──────────────────────────────────────────────────┤
# │ 유방암 BRCA  │ pathology (H&E), histology (IHC HER2/ER/PR)     │
# │ 폐암 LUAD    │ ct (LDCT 저선량 CT), xray (흉부 X-ray)          │
# │ 대장암 CRC   │ pathology (H&E), histology (MSI 판독)           │
# │ 뇌종양 GBM   │ ct (뇌 CT), pathology (H&E)                     │
# │ 피부암 MEL   │ pathology (더모스코피 이미지)                     │
# └──────────────┴──────────────────────────────────────────────────┘

VALID_IMAGE_TYPES = ("pathology", "histology", "ct", "xray")

# 이미지 타입별 예상 Feature Extractor 출력 차원
IMAGE_DIM_GUIDE = {
    "pathology": "ResNet-50 → 2048 / ViT-B → 768 / CTransPath → 768",
    "histology": "ResNet-50 → 2048 / ViT-B → 768",
    "ct":        "3D-ResNet → 512 / Med3D → 512",
    "xray":      "DenseNet-121 → 1024 / CheXNet → 1024",
}


class MedicalImageEncoder(BaseModalEncoder):
    """의료 영상 통합 Encoder (향후 구현 예정).

    image_type 파라미터로 이미지 종류를 구분:
      - pathology : H&E 병리 슬라이드 tile feature
      - histology : IHC/특수염색 조직학 이미지
      - ct        : CT 슬라이스 3D feature
      - xray      : 흉부/유방 X-ray feature

    예상 input_dim: feature extractor 출력 차원
      - ResNet-50 → 2048, ViT-B/CTransPath → 768
      - 3D-ResNet/Med3D → 512, DenseNet-121/CheXNet → 1024

    사용 예시 (구현 완료 후):
        enc = MedicalImageEncoder(image_type="pathology", input_dim=768)
        enc = MedicalImageEncoder(image_type="ct", input_dim=512)
    """
    modal_name = "medical_image"
    input_dim = 0   # TBD — feature extractor 확정 후 결정
    output_dim = 128

    def __init__(
        self,
        image_type: str = "pathology",
        input_dim: int = 0,
        output_dim: int = 128,
        dropout: float = 0.2,
    ):
        if image_type not in VALID_IMAGE_TYPES:
            raise ValueError(
                f"image_type='{image_type}' 미지원. "
                f"가능한 값: {VALID_IMAGE_TYPES}"
            )
        super().__init__(input_dim, output_dim, dropout)
        self.image_type = image_type

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError(
            f"MedicalImageEncoder(image_type='{self.image_type}')는 "
            f"아직 구현되지 않았습니다.\n"
            f"  예상 input_dim: {IMAGE_DIM_GUIDE.get(self.image_type, 'TBD')}\n"
            f"  Feature extractor 확정 후 구현 예정."
        )

    @classmethod
    def get_modal_name(cls) -> str:
        return cls.modal_name

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}"
                f"(type={self.image_type}, "
                f"in={self.input_dim}, out={self.output_dim})")


# ── 4-2. 비이미지 계열 ──────────────────────────────────────────

class WGSEncoder(BaseModalEncoder):
    """Whole Genome Sequencing Encoder (향후 구현 예정).

    입력 데이터:
      - Somatic mutation burden (TMB)
      - Copy Number Variation (CNV) segments
      - Structural Variants (SV)
      - Mutational signatures (COSMIC SBS)
      - Driver gene mutation status (TP53, PIK3CA, BRCA1/2 등)
    출처: GDC/TCGA WGS BAM → variant calling pipeline
    예상 input_dim: 500~5,000 (variant feature vector 크기에 따라 결정)

    질환별 활용:
      - 유방암 BRCA : BRCA1/2 germline + somatic, HRD score
      - 폐암 LUAD   : EGFR/ALK/KRAS mutation, TMB
      - 대장암 CRC  : MSI status, APC/KRAS/TP53 pathway
    """
    modal_name = "wgs"
    input_dim = 0   # TBD
    output_dim = 128

    def __init__(self, input_dim: int = 0, output_dim: int = 128, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError(
            "WGSEncoder는 아직 구현되지 않았습니다. "
            "WGS variant feature 스키마 확정 후 구현 예정."
        )


class EMREncoder(BaseModalEncoder):
    """Electronic Medical Record Encoder (향후 구현 예정).

    입력 데이터:
      - 진단코드 (ICD-10: C50 유방암, C34 폐암 등)
      - 투약이력 (처방 ATC 코드, 용량, 기간)
      - 바이탈 사인 (BP, HR, BT, RR, SpO2)
      - 검사수치 (CBC, LFT, RFT, tumor markers)
      - 수술/시술 이력
      - 입원/외래 방문 패턴
    출처: 병원 EMR (OMOP CDM 변환 후 feature화)
    예상 input_dim: 50~500 (구조화 feature 수에 따라 결정)

    질환별 활용:
      - 유방암 BRCA : ER/PR/HER2 status, Ki-67, 선행항암 반응
      - 폐암 LUAD   : ECOG PS, 폐기능검사, PD-L1 TPS
      - 공통        : 나이, BMI, 동반질환 CCI score
    """
    modal_name = "emr"
    input_dim = 0   # TBD
    output_dim = 64

    def __init__(self, input_dim: int = 0, output_dim: int = 64, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError(
            "EMREncoder는 아직 구현되지 않았습니다. "
            "임상기록 feature 스키마 (OMOP CDM) 확정 후 구현 예정."
        )


class AlphaFoldEncoder(BaseModalEncoder):
    """AlphaFold 단백질 구조 Encoder (향후 구현 예정).

    입력 데이터:
      - AlphaFold2/3 predicted 3D structure embedding
      - pLDDT confidence score per residue
      - ESM-2 protein language model embedding
      - Binding site pocket descriptors
      - Drug-protein docking score features
    출처: AlphaFold DB + ESM-2 + AutoDock-GPU
    예상 input_dim: 320~1,280 (ESM-2 small→320, large→1,280)

    질환별 활용:
      - 유방암 BRCA : HER2(ERBB2) 구조 + 약물 결합부위 예측
      - 폐암 LUAD   : EGFR kinase domain 구조, ALK fusion protein
      - 공통        : drug-target docking affinity 기반 재창출
    """
    modal_name = "alphafold"
    input_dim = 0   # TBD
    output_dim = 128

    def __init__(self, input_dim: int = 0, output_dim: int = 128, dropout: float = 0.2):
        super().__init__(input_dim, output_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError(
            "AlphaFoldEncoder는 아직 구현되지 않았습니다. "
            "ESM-2/AlphaFold embedding 차원 확정 후 구현 예정."
        )


# ═══════════════════════════════════════════════════════════════════
# 5. 자동 등록
# ═══════════════════════════════════════════════════════════════════

# 기존 5개 (READY)
for _cls in [CRISPREncoder, MorganFPEncoder, LINCSEncoder,
             TargetEncoder, DrugDescEncoder]:
    registry.register(_cls.modal_name, _cls)

# 향후 Stub (TBD)
for _cls in [MedicalImageEncoder, WGSEncoder, EMREncoder, AlphaFoldEncoder]:
    registry.register(_cls.modal_name, _cls)


# ═══════════════════════════════════════════════════════════════════
# Smoke Test
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  Modal Interface Smoke Test")
    print("=" * 70)

    # 1. Registry 전체 조회
    print(f"\n  {registry}")
    print(f"\n  {'name':20s}  {'class':25s}  {'in':>6s}  {'out':>4s}  status")
    print(f"  {'─'*20}  {'─'*25}  {'─'*6}  {'─'*4}  {'─'*6}")
    for m in registry.list_modals():
        print(f"  {m['name']:20s}  {m['class']:25s}  "
              f"{str(m['input_dim']):>6s}  {str(m['output_dim']):>4s}  "
              f"[{m['status']}]")

    # 2. 기존 5개 forward 테스트
    batch = 4
    print(f"\n  Forward test (batch={batch}):")
    for name, dim in [("crispr", 18310), ("morgan_fp", 2048),
                      ("lincs", 5), ("target", 10), ("drug_desc", 9)]:
        enc = registry.get(name)()
        out = enc(torch.randn(batch, dim))
        print(f"    {enc}  →  {tuple(out.shape)}")

    # 3. MedicalImageEncoder image_type 테스트
    print(f"\n  MedicalImageEncoder image_type test:")
    for itype in VALID_IMAGE_TYPES:
        enc = MedicalImageEncoder(image_type=itype)
        try:
            enc(torch.randn(batch, 1))
        except NotImplementedError:
            print(f"    image_type={itype:12s}  → NotImplementedError OK")

    # 4. 비이미지 Stub 테스트
    print(f"\n  Non-image Stub test:")
    for name in ["wgs", "emr", "alphafold"]:
        enc = registry.get(name)()
        try:
            enc(torch.randn(batch, 1))
        except NotImplementedError:
            print(f"    {name:20s}  → NotImplementedError OK")

    # 5. get_modal_name 테스트
    print(f"\n  get_modal_name() test:")
    for name in ["crispr", "morgan_fp", "lincs", "target", "drug_desc",
                  "medical_image", "wgs", "emr", "alphafold"]:
        cls = registry.get(name)
        print(f"    {cls.__name__:25s} → '{cls.get_modal_name()}'")

    print(f"\n{'='*70}")
    print("  All tests passed!")
    print(f"{'='*70}")

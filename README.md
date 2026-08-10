<div align="center">

# MirrorWorld: Taming Video Diffusion Models for Mirror Reflection Generation

**Youjun Zhao<sup>1</sup>**, **Alex Warren<sup>2</sup>**, **Gary K. L. Tam<sup>2</sup>**, **Rynson W. H. Lau<sup>1</sup>**

<sup>1</sup>City University of Hong Kong &nbsp;&nbsp; <sup>2</sup>Swansea University

[**📄[arXiv]**](https://arxiv.org/abs/2608.07463) **|** [**🔥[Project]**](https://youjunzhao.github.io/MirrorWorld/) **|** [**💻[Code]**](https://github.com/YoujunZhao/MirrorWorld) **|** [**🧩[Data]**](https://youjunzhao.github.io/MirrorWorld/#benchmark)

</div>

## 🌟 Overview

Recent advances in video diffusion models (VDMs) have enabled high-fidelity video synthesis. However, generating mirror reflections remains challenging because the content within a mirror must remain consistent with the surrounding scene. Existing VDMs are not specifically designed to model scene-to-mirror relationships, which can lead to reflections with incorrect content or inconsistent spatial arrangements.

MirrorWorld is a reflection-aware video inpainting framework that models scene-to-mirror relationships during generation. It addresses two complementary questions: **what should be reflected** and **how it should be arranged**.

<p align="center">
  <a href="https://youjunzhao.github.io/MirrorWorld/">
    <img src="https://raw.githubusercontent.com/YoujunZhao/MirrorWorld/page/static/images/qualitative.webp" width="900" alt="MirrorWorld qualitative comparison">
  </a>
</p>

## 🔥 Highlights

- **Semantic Relation Distillation (SRD)** transfers relational information from a frozen visual foundation model to associate visible scene content with the missing mirror region.
- **Geometric Transformation Alignment (GTA)** learns a feature-space transformation that guides the spatial arrangement of reflected content over time.
- A unified benchmark repurposes **VMD-D, ZOOM, MMD, and DVMD-D** for video mirror reflection reconstruction with source-video-level splits.
- MirrorWorld improves mirror-region reconstruction over representative image-based reflection methods and strong video inpainting baselines.

## 🎥 Demo

The complete set of playable comparisons, masked inputs, generated videos, and additional MirrorWorld results is available on the [project page](https://youjunzhao.github.io/MirrorWorld/).

## 📈 Quantitative Results

Metrics are computed inside mirror regions. Best results are highlighted.

| Method | Type | PSNR ↑ | SSIM ↑ | LPIPS ↓ | FVD ↓ |
|:--|:--:|--:|--:|--:|--:|
| MirrorFusion | Image | 9.508 | 0.293 | 0.699 | 513.062 |
| MirrorVerse | Image | 9.666 | 0.312 | 0.680 | 416.146 |
| VideoPainter | Video | 11.282 | 0.399 | 0.606 | 229.558 |
| VACE | Video | 13.537 | 0.489 | 0.493 | 191.617 |
| **MirrorWorld (Ours)** | **Video** | **14.005** | **0.504** | **0.488** | **184.868** |

## 🧩 Benchmark

The benchmark combines four existing video mirror datasets into a unified reflection reconstruction task:

- **1,142** training clips
- **100** test clips
- Up to **49 frames per clip**
- **4** source datasets: VMD-D, ZOOM, MMD, and DVMD-D

The split is performed at the source-video level to avoid leakage between related clips.

## 🧠 Method

### Semantic Relation Distillation (SRD)

SRD uses a frozen visual foundation model as a relational reference. It aligns similarity relations between mirror-region tokens and visible-scene tokens, teaching the diffusion representation which surrounding content is semantically associated with the missing reflection.

### Geometric Transformation Alignment (GTA)

GTA predicts an affine feature-space transformation from a local temporal context and differentiably warps visible-scene features toward the mirror region. This constrains where associated content should appear while maintaining temporal stability.

## 📄 Citation

If you find MirrorWorld useful, please consider citing:

```bibtex
@misc{mirrorworld,
  title        = {MirrorWorld: Taming Video Diffusion Models for Mirror Reflection Generation},
  author       = {Youjun Zhao and Alex Warren and Gary K. L. Tam and Rynson W. H. Lau},
  year         = {2026},
  eprint       = {2608.07463},
  archivePrefix = {arXiv},
  primaryClass = {cs.CV},
  url          = {https://arxiv.org/abs/2608.07463},
}
```

## 🔗 Links

- [Project page](https://youjunzhao.github.io/MirrorWorld/)
- [arXiv paper](https://arxiv.org/abs/2608.07463)
- [Code](https://github.com/YoujunZhao/MirrorWorld)
- [Benchmark overview](https://youjunzhao.github.io/MirrorWorld/#benchmark)

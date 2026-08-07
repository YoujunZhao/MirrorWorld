<div align="center">

# MirrorWorld: Taming Video Diffusion Models for Mirror Reflection Generation

**Youjun Zhao<sup>1</sup>**, **Alex Warren<sup>2</sup>**, **Gary K.L. Tam<sup>2</sup>**, **Rynson W.H. Lau<sup>1</sup>**

<sup>1</sup>City University of Hong Kong &nbsp;&nbsp; <sup>2</sup>Swansea University

### [📄 Arxiv](https://youjunzhao.github.io/MirrorWorld/) &nbsp; | &nbsp; [🔥 Project](https://youjunzhao.github.io/MirrorWorld/) &nbsp; | &nbsp; [💻 Code](https://github.com/YoujunZhao/MirrorWorld) &nbsp; | &nbsp; [🤗 Hugging Face](https://youjunzhao.github.io/MirrorWorld/)

</div>

## Abstract

Recent video diffusion models can synthesize high-fidelity videos, but they do not explicitly model the relationship between a visible scene and its mirror. As a result, generated reflections may contain the wrong content or place semantically related content at an inconsistent location.

**MirrorWorld** is a reflection-aware video inpainting framework for mirror reflection generation. It separates the problem into two complementary questions:

- **What should be reflected?** Semantic Relation Distillation (SRD) transfers relational knowledge from a frozen visual foundation model to associate mirror regions with reflection-relevant visible content.
- **How should it appear?** Geometric Transformation Alignment (GTA) learns a temporally conditioned feature-space transformation that guides the spatial arrangement of the associated content inside the mirror.

We also construct a unified benchmark for video mirror reflection reconstruction by repurposing four existing video mirror datasets: VMD-D, ZOOM, MMD, and DVMD-D. The project page provides matched comparisons with MirrorFusion, MirrorVerse, VideoPainter, and VACE, together with additional MirrorWorld results.

## The task

Given a video with the mirror region masked, MirrorWorld reconstructs the missing reflection while preserving its semantic relationship to the visible scene and its geometric arrangement over time.

## Method

### Semantic Relation Distillation (SRD)

A frozen VideoMAEv2 visual foundation model provides reference features. SRD aligns the cosine-similarity relations between mirror-region tokens and visible-scene tokens, transferring scene-to-mirror semantic structure into the diffusion representation.

### Geometric Transformation Alignment (GTA)

GTA builds a source feature map from visible-scene tokens and predicts an affine transformation from a local five-frame temporal context. The current-frame features are differentiably warped into the mirror region, encouraging stable spatial placement of reflection content.

## Benchmark

The benchmark unifies four existing video mirror datasets under a reflection reconstruction protocol. Evaluation focuses on mirror-region reconstruction quality and video-level consistency, using PSNR, SSIM, LPIPS, and FVD.

## Project page

The interactive project page is hosted from the `page` branch:

- Website: [https://youjunzhao.github.io/MirrorWorld/](https://youjunzhao.github.io/MirrorWorld/)
- Hosting branch: `page`
- Main branch: documentation and project overview

## Citation

BibTeX placeholder — update this entry with the final arXiv or publication metadata.

```bibtex
@article{mirrorworld2026,
  title   = {MirrorWorld: Taming Video Diffusion Models for Mirror Reflection Generation},
  author  = {Zhao, Youjun and Warren, Alex and Tam, Gary K. L. and Lau, Rynson W. H.},
  journal = {arXiv preprint},
  year    = {2026},
  note    = {BibTeX placeholder; update with final publication metadata}
}
```

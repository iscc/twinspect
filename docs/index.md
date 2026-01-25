# ISCC - Evaluation

**Evaluating the International Standard Content Code (ISCC)**

*A Comprehensive and Scientific Approach to Understand the Capabilities of ISCC*

!!! success "ISCC Status"

    The International Standard Content Code was published as ISO 24138:2024 in May 2024. See
    https://www.iso.org/standard/77899.html

## Digital Content Identification

Welcome to the exploration and evaluation of the **International Standard Content Code (ISCC)**. In
the digital landscape, accurately identifying and cataloguing content is a critical task. The ISCC
is designed to address this need as a versatile, universal identifier for digital content,
encompassing a broad spectrum of formats like text, image, audio, and video.

## Understanding ISCC

With any innovative technology comes a learning curve, and the ISCC is no exception. Across various
disciplines, the ISCC's unique approach has sparked many questions:

- Registration agencies are seeking to understand how this differs from established standard
    identifiers.
- Content recognition specialists are interested in its capabilities in granular content matching.
- Software developers, accustomed to cryptographic hashes for secure data identification, are
    curious about how the ISCC compares.

Our aim is to provide clear insights into the capabilities of the ISCC, dispel any misconceptions,
and deliver a well-rounded understanding of this new and exciting technology.

## Introducing TwinSpect

!!! abstract inline end "Purpose"

    The primary purpose of TwinSpect is to assess to which extent the ISCC is capable of clustering and
    matching similar content.

To address concerns and provide clarity, we've developed
[**TwinSpect**](https://github.com/iscc/twinspect) — a comprehensive open-source framework
engineered for evaluating the ISCC in an accessible and scientifically robust manner. TwinSpect is
built on widely recognized metrics from the field of information retrieval and makes use of various
public and private datasets selected and built to fit our evaluation objectives.

While TwinSpect is specifically designed to evaluate the ISCC, its adaptability goes beyond.
TwinSpect can easily be extended with custom algorithms, datasets, transformations and metrics.

## ISCC & AI

As we enter the era of Artificial Intelligence, where content creation and distribution are becoming
increasingly automated, the role of the ISCC in ensuring accurate content identification, and
improving the trust in content provenance becomes even more critical.

!!! note "Semantic-Code"

    The ISO 24138:2024 standard reserves prefixes for the ISCC Semantic-Code which employs Deep Learning
    and Artificial Intelligence techniques to create ISCC-UNITs that match similarity based on the
    high-level understanding of concepts. Draft implementations are available for text
    ([iscc-sct](https://github.com/iscc/iscc-sct)) and image
    ([iscc-sci](https://github.com/iscc/iscc-sci)) content. For example, the Semantic-Code for textual
    content is capable of creating similar codes for the same text translated to different languages
    (cross-lingual similarity matching). Evaluations of Semantic-Codes are planned for TwinSpect.

## What´s Ahead

In the following pages, we will provide a detailed look at the ISCC, explain the TwinSpect
evaluation framework, and share the findings from our evaluation. Our goal is to give you a thorough
understanding of the ISCC and its potential, in a clear, concise, and business-focused manner.

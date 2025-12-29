# Introduction

## What is PyPSA-Earth-Status?

**PyPSA-Earth-Status** is an open-source Python package designed to **validate PyPSA energy system models against real-world data anywhere on Earth**.

Energy system models are increasingly used to inform research, policy, and investment decisions. However, ensuring that a model represents today’s energy system remains a persistent challenge. PyPSA-Earth-Status addresses this gap by providing **automated, transparent, and reproducible validation workflows** for energy models including PyPSA networks and beyond.

The package compares user-provided PyPSA networks with **authoritative, state-of-the-art reference datasets**, such as those from IRENA, IEA, and other widely used public sources. It is modular and extensible, allowing users to customize validation metrics and incorporate additional data sources as needed. Contributions from the community are highly encouraged to expand its capabilities.

## Why model validation matters

Even well-designed energy system models can produce misleading insights if they are poorly calibrated to real-world conditions. Common challenges include:

- Installed capacities that deviate from observed statistics  
- Implausible optimized capacities after model solving  
- Inconsistent transmission capacities across borders  
- Demand levels that do not match historical consumption  

Validating these aspects manually is time-consuming, error-prone, and often inconsistent across studies.

**PyPSA-Earth-Status standardizes and automates this process**, allowing modelers to:

- Quickly assess the realism of their networks  
- Identify discrepancies early in the modeling workflow  
- Improve transparency and reproducibility  
- Focus more time on scenario design and analysis rather than data checking  

## What does PyPSA-Earth-Status validate?

PyPSA-Earth-Status performs structured comparisons between a PyPSA network and reference statistics, including:

- **Installed capacities**  
  - Generator and storage capacities (`p_nom`)
- **Optimized capacities**  
  - Generator and storage capacities after optimization (`p_nom_opt`)
- **Transmission infrastructure**  
  - Line capacities (`s_nom`), including cross-border links
- **Electricity demand**  
  - Comparison with historical consumption data
- And more to come with your contributions! 

The results are presented as **tables and visualizations**, making discrepancies easy to interpret and communicate.

## Reference data sources

The validation framework relies on curated datasets from leading institutions, including:

- Electricity demand data from *Our World in Data*  
- Installed generation capacities from *IRENA* and *IEA*  
- Cross-border transmission capacities from the *Global Transmission Database*  

All reference data and processing steps are fully transparent and reproducible.

## Open and collaborative development

PyPSA-Earth-Status is an open, community-driven project. Contributions are welcome in many forms, including:

- New validation metrics  
- Additional reference datasets  
- Improvements to visualizations and reporting  
- Extensions to other energy carriers or sectors  

By building shared validation standards, PyPSA-Earth-Status aims to strengthen **credibility, comparability, and trust** in open energy system modeling worldwide.

# Public dataset provenance and access

Source checks performed 2026-10-21:

- CWRU official index: https://engineering.case.edu/bearingdatacenter/download-data-file — accessible, links to normal and 12/48 kHz MATLAB vibration recordings. Discovery traverses official linked data pages. Files are not downloaded without an explicit downloader command and access-term acknowledgement.
- NASA PHM 2009 official resource: https://c3.ndc.nasa.gov/dashlink/resources/997/ — fetch timed out. Official NASA challenge listing https://c3.ndc.nasa.gov/dashlink/projects/94/resources/ identifies the gearbox challenge. No guessed archive URL is embedded.
- Paderborn historical source: https://mb.uni-paderborn.de/kat/forschung/datacenter/bearing-datacenter — returned 404. The publisher's paper https://mb.uni-paderborn.de/fileadmin-mb/kat/PDF/Veroeffentlichungen/20160703_PHME16_CM_bearing.pdf states CC BY-NC 4.0 and attribution expectations. Current access and commercial permission must be reviewed with the publisher.

Public downloads preserve raw files and adjacent URL/size/SHA256/ETag metadata. Publisher checksum verification is distinct from recording a local hash. Processed features are separate CSVs with recording identity and nonoverlapping signal windows. The generic numeric/MATLAB channel importer is usable for accessible source files; nested proprietary structures require explicit channel export. No public-energy validation claim is made.

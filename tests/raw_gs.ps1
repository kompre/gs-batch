gswin64c `
    -sDEVICE=pdfwrite `
    -o tests/assets/output/pdfa_def.pdf `
    -dPDFSETTINGS=/ebook `
    -dPDFACompatibilityPolicy=1 `
    -sColorConversionStrategy=RGB `
    --permit-file-read=C:/Users/s.follador/Documents/github/gs-batch/gs_batch/assets/srgb.icc `
    -dPDFA=2 `
    -c "/ICCProfile (C:/Users/s.follador/Documents/github/gs-batch/gs_batch/assets/srgb.icc) def" -f `
    C:/Users/s.follador/Documents/github/gs-batch/gs_batch/assets/PDFA_def.ps `
    C:/Users/s.follador/Documents/github/gs-batch/tests/assets/originals/file_0_corrupted.pdf
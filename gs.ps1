
    # gswin64c `
    #     -sDEVICE=pdfwrite `
    #     -dPDFACompatibilityPolicy=1 `save output of -dpdfinfo ghostscript
    #     -dPDFACompatibilityPolicy=2 `
    #     -dPDFA=1 `
    #     -dPDFA=2 `
    #     -sColorConversionStrategy=RGB `
    #     -o rel_mat.pdf `
    #     -q `
    #     '.\[23064 - BALSAMO - Treviso - Santa Bona Nuova] Relazione sui materiali.pdf'

# gswin64c ` -dNOSAFER -c "(c.pdf) (r) file runpdfbegin pdfpagecount = quit"

gswin64c -sDEVICE=pdfwrite -q -o '.\ps.pdf' '.\mat.pdf' 
# PDF Actions

---

{: .note }
> To use actions in this category, use this include statement:
>
> ```
> #include 'actions/pdf'
> ```

### Get PDF Text

Get text from PDF.

```
getPDFText(variable pdfFile, bool ?richText = false, bool ?combinePages = true, text ?headerText, text ?footerText)
```

---

### Make Image from PDF Page

Returns an image of the provided PDF.

```
enum colorSpace {
    'RGB',
    'Gray',
}

makeImageFromPDFPage(variable pdf, colorSpace ?colorSpace = "RGB", text ?pageResolution = "300")
```

---

### Make PDF

Make a PDF file using the provided input.

```
enum PDFMergeBehaviors {
    'Append',
    'Shuffle',
}

makePDF(variable input, bool ?includeMargin = false, PDFMergeBehaviors ?mergeBehavior = "Append")
```

---

### Optimize PDF

Returns a compressed version of the PDF.

```
optimizePDF(variable pdfFile)
```

---

### Split PDF

Splits a PDF into pages.

```
splitPDF(variable pdf): array
```

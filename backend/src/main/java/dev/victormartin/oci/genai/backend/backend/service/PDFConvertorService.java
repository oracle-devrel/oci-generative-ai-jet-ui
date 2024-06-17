package dev.victormartin.oci.genai.backend.backend.service;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.ResourceUtils;

import java.io.File;
import java.io.IOException;

@Service
public class PDFConvertorService {
    Logger log = LoggerFactory.getLogger(PDFConvertorService.class);

    public String convert(String filePath) {
        try {
            File file = ResourceUtils.getFile(filePath);
            PDDocument doc = Loader.loadPDF(file);
            return new PDFTextStripper().getText(doc);
        } catch (IOException e) {
            log.error(e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
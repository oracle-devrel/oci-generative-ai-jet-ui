package dev.victormartin.oci.genai.backend.backend.controller;


import dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService;
import dev.victormartin.oci.genai.backend.backend.service.PDFConvertorService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;

@RestController
public class PDFConvertorController {
    Logger log = LoggerFactory.getLogger(PDFConvertorController.class);

    @Value("${storage.path}")
    String storagePath;

    @Value("${genai.summarization_model_id}")
    String summarizationModelId;

    @Autowired
    OCIGenAIService ociGenAIService;

    @Autowired
    PDFConvertorService pdfConvertorService;

    @Autowired
    SummaryController summaryController;

    @PostMapping("/api/upload")
    public String fileUploading(@RequestParam("file") MultipartFile multipartFile) {
        String filename = StringUtils.cleanPath(multipartFile.getOriginalFilename());
        log.info("File uploaded {} {} bytes ({})", filename, multipartFile.getSize(), multipartFile.getContentType());
        try {
            if (filename.contains("..")) {
                throw new Exception("Filename contains invalid path sequence");
            }
            if (multipartFile.getBytes().length > (1024 * 1024)) {
                throw new Exception("File size exceeds maximum limit");
            }
            String fileDestinationPath = StringUtils.cleanPath(storagePath);
            File file = new File(fileDestinationPath + File.separator + filename);
            multipartFile.transferTo(file);
            log.info("File destination path: {}", file.getAbsolutePath());
            String convertedText = pdfConvertorService.convert(file.getAbsolutePath());
            String summaryText = ociGenAIService.summaryText(convertedText, summarizationModelId);
            log.info("Summary text: {}(...)", summaryText.substring(0, 40));
            summaryController.handleSummary(summaryText);
            return summaryText;
        } catch (MaxUploadSizeExceededException maxUploadSizeExceededException) {
            log.error(maxUploadSizeExceededException.getMessage());
            throw new RuntimeException(maxUploadSizeExceededException);
        } catch (Exception e) {
            log.error(e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
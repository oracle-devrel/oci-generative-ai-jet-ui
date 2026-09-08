package com.example.news;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;

import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;

public class Utils {
    public static String readFile(String fileName) {
        try {
            Resource resource = new ClassPathResource(fileName);
            File file = resource.getFile();
            return new String(Files.readAllBytes(file.toPath()));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}

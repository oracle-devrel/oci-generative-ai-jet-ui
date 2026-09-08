package com.example.news.events.parser;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class Splitter {
    private int chunkSize;
    private final Pattern pattern;

    public Splitter(@Value("${new.chunking.characters:2000}") int chunkSize,
                    Pattern pattern) {
        this.chunkSize = chunkSize;
        this.pattern = pattern;
    }

    public List<String> split(String text) {
        List<String> chunks = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return chunks;
        }
        Matcher matcher = pattern.matcher(text);
        int startPos = 0, endPos;
        StringBuilder currentChunk = new StringBuilder();
        while (matcher.find()) {
            endPos = matcher.start() + 1;
            String sentence = text.substring(startPos, endPos);
            currentChunk.append(sentence);
            startPos = endPos;
            if (currentChunk.length() >= chunkSize) {
                chunks.add(currentChunk.toString().trim());
                currentChunk.setLength(0);
            }
        }

        // Capture any remaining text after the last match
        if (startPos < text.length()) {
            currentChunk.append(text.substring(startPos));
        }

        if (!currentChunk.isEmpty()) {
            chunks.add(currentChunk.toString().trim());
        }

        return chunks;
    }
}

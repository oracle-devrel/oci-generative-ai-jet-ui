package com.example.news.events.parser;

import java.util.regex.Pattern;

import tools.jackson.databind.ObjectMapper;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ParserConfiguration {
    @Bean
    Pattern sentencePattern() {
        // Regular expression pattern to match one or more whitespace characters followed by a period, question mark, or exclamation mark
        return Pattern.compile("[.!?]");
    }
}

package dev.victormartin.oci.genai.backend.backend;

import com.oracle.bmc.ClientConfiguration;
import com.oracle.bmc.retrier.RetryConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ClientConfigurationBean {
    @Bean
    public ClientConfiguration clientConfiguration() {
        ClientConfiguration clientConfiguration =
                ClientConfiguration.builder()
                        .readTimeoutMillis(240000)
                        .retryConfiguration(RetryConfiguration.NO_RETRY_CONFIGURATION)
                        .build();
        return clientConfiguration;
    }
}

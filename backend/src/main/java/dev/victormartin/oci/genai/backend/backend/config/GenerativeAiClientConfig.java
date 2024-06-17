package dev.victormartin.oci.genai.backend.backend.config;

import com.oracle.bmc.ClientConfiguration;
import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.Region;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.auth.okeworkloadidentity.OkeWorkloadIdentityAuthenticationDetailsProvider;
import com.oracle.bmc.generativeai.GenerativeAiClient;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import java.io.IOException;

@Configuration
public class GenerativeAiClientConfig {

    Logger logger = LoggerFactory.getLogger(GenerativeAiClientConfig.class);

    @Autowired
    private Environment environment;

    @Autowired
    ClientConfiguration clientConfiguration;

    @Value("${genai.endpoint}")
    private String ENDPOINT;
    @Value("${genai.region}")
    private String regionCode;
    @Value("${genai.config.location}")
    private String CONFIG_LOCATION;
    @Value("${genai.config.profile}")
    private String CONFIG_PROFILE;

    @Value("${genai.chat_model_id}")
    private String chatModelId;
    
    @Value("${genai.summarization_model_id}")
    private String summarizationModelId;

    private Region region;

    @PostConstruct
    private void postConstruct() {
        logger.info("Region Code: " + regionCode);
        region = Region.fromRegionCode(regionCode);
    }

    @Bean
    GenerativeAiClient genAiClient() throws IOException {
        String[] activeProfiles = environment.getActiveProfiles();
        String profile = activeProfiles[0];
        if (profile.equals("production")) {
            return instancePrincipalConfig();
        } else {
            return localConfig();
        }
    }

    GenerativeAiClient instancePrincipalConfig() throws IOException {
        final OkeWorkloadIdentityAuthenticationDetailsProvider okeProvider = new OkeWorkloadIdentityAuthenticationDetailsProvider.OkeWorkloadIdentityAuthenticationDetailsProviderBuilder()
                .build();
        // final InstancePrincipalsAuthenticationDetailsProvider provider =
        // new
        // InstancePrincipalsAuthenticationDetailsProvider.InstancePrincipalsAuthenticationDetailsProviderBuilder().build();

        GenerativeAiClient generativeAiClient = new GenerativeAiClient(okeProvider, clientConfiguration);
        generativeAiClient.setRegion(okeProvider.getRegion());
        generativeAiClient.setEndpoint(ENDPOINT);
        return generativeAiClient;
    }

    GenerativeAiClient localConfig() throws IOException {
        // Configuring the AuthenticationDetailsProvider. It's assuming there is a
        // default OCI config file
        // "~/.oci/config", and a profile in that config with the name defined in
        // CONFIG_PROFILE variable.
        final ConfigFileReader.ConfigFile configFile = ConfigFileReader.parse(CONFIG_LOCATION, CONFIG_PROFILE);
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        GenerativeAiClient generativeAiClient = new GenerativeAiClient(provider,
                clientConfiguration);
        generativeAiClient.setEndpoint(ENDPOINT);
        generativeAiClient.setRegion(region);
        return generativeAiClient;
    }
}

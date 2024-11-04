package dev.victormartin.oci.genai.backend.backend.service;

import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.Region;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.auth.InstancePrincipalsAuthenticationDetailsProvider;
import com.oracle.bmc.auth.okeworkloadidentity.OkeWorkloadIdentityAuthenticationDetailsProvider;
import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

import java.io.IOException;

@Service
public class GenAiInferenceClientService {

    Logger log = LoggerFactory.getLogger(GenAiInferenceClientService.class);

    private GenerativeAiInferenceClient client;

    @Autowired
    private Environment environment;

    @Value("${genai.region}")
    private String regionCode;
    @Value("${genai.config.location}")
    private String CONFIG_LOCATION;
    @Value("${genai.config.profile}")
    private String CONFIG_PROFILE;

    @PostConstruct
    private void postConstruct() {
        String[] activeProfiles = environment.getActiveProfiles();
        String profile = activeProfiles[0];
        log.info("Profile: {}", profile);
        switch (profile) {
            case "oke":
                okeGenAiClient();
                break;
            case "compute":
                instancePrincipalClient();
                break;
            default:
                localConfig();
                break;
        }
    }

    private void okeGenAiClient() {
        final OkeWorkloadIdentityAuthenticationDetailsProvider provider = new OkeWorkloadIdentityAuthenticationDetailsProvider
                .OkeWorkloadIdentityAuthenticationDetailsProviderBuilder()
                .build();
        GenerativeAiInferenceClient okeClient = GenerativeAiInferenceClient.builder()
                .region(Region.fromRegionCode(regionCode))
                .build(provider);
        setClient(okeClient);
    }

    private void instancePrincipalClient() {
        final InstancePrincipalsAuthenticationDetailsProvider provider = new InstancePrincipalsAuthenticationDetailsProvider.InstancePrincipalsAuthenticationDetailsProviderBuilder()
                .build();

        GenerativeAiInferenceClient okeClient = GenerativeAiInferenceClient.builder()
                .region(Region.fromRegionCode(regionCode))
                .build(provider);
        setClient(okeClient);
    }

    private void  localConfig() {
        final ConfigFileReader.ConfigFile configFile;
        try {
            configFile = ConfigFileReader.parse(CONFIG_LOCATION, CONFIG_PROFILE);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        GenerativeAiInferenceClient okeClient = GenerativeAiInferenceClient.builder()
                .region(Region.fromRegionCode(regionCode))
                .build(provider);
        setClient(okeClient);
    }

    public GenerativeAiInferenceClient getClient() {
        return client;
    }

    public void setClient(GenerativeAiInferenceClient client) {
        this.client = client;
    }
}

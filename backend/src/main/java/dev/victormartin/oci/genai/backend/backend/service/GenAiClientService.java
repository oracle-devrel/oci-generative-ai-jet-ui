package dev.victormartin.oci.genai.backend.backend.service;

import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.Region;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.auth.InstancePrincipalsAuthenticationDetailsProvider;
import com.oracle.bmc.auth.okeworkloadidentity.OkeWorkloadIdentityAuthenticationDetailsProvider;
import com.oracle.bmc.generativeai.GenerativeAiClient;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

import java.io.IOException;

@Service
public class GenAiClientService {

    Logger log = LoggerFactory.getLogger(GenAiClientService.class);

    @Autowired
    private Environment environment;

    private GenerativeAiClient client;

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
        switch (profile) {
            case "oke":
                okeGenAiClient();
                break;
            case "compute":
                instancePrincipalClient();
                break;
            default:
                localClient();
                break;
        }
    }

    private void okeGenAiClient() {
        final OkeWorkloadIdentityAuthenticationDetailsProvider provider = new OkeWorkloadIdentityAuthenticationDetailsProvider
                .OkeWorkloadIdentityAuthenticationDetailsProviderBuilder()
                .build();
        GenerativeAiClient okeClient = GenerativeAiClient.builder()
                .region(Region.fromRegionCode(regionCode))
                .build(provider);
        setClient(okeClient);
    }


    private void instancePrincipalClient() {
         final InstancePrincipalsAuthenticationDetailsProvider provider = new InstancePrincipalsAuthenticationDetailsProvider
                 .InstancePrincipalsAuthenticationDetailsProviderBuilder()
                 .build();

        GenerativeAiClient instancePrinciplaClient = GenerativeAiClient.builder()
                .region(Region.fromRegionCode(regionCode))
                .build(provider);
        setClient(instancePrinciplaClient);
    }

    private void localClient() {
        final ConfigFileReader.ConfigFile configFile;
        try {
            configFile = ConfigFileReader.parse(CONFIG_LOCATION, CONFIG_PROFILE);
        } catch (IOException e) {
            log.error("Failed to load config file at {}", CONFIG_LOCATION);
            log.error(e.getMessage());
            throw new RuntimeException(e);
        }
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        GenerativeAiClient localClient = GenerativeAiClient.builder()
                .region(Region.fromRegionCode(regionCode))
                .build(provider);
        setClient(localClient);
    }

    public GenerativeAiClient getClient() {
        return client;
    }

    public void setClient(GenerativeAiClient client) {
        this.client = client;
    }
}

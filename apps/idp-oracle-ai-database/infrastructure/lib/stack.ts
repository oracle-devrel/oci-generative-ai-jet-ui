import { Stack, type StackProps, Duration, CfnOutput, RemovalPolicy } from "aws-cdk-lib";
import type { Construct } from "constructs";
import { Bucket, BlockPublicAccess, BucketEncryption } from "aws-cdk-lib/aws-s3";
import {
  Distribution,
  ViewerProtocolPolicy,
  CachePolicy,
  AllowedMethods,
  PriceClass,
  ResponseHeadersPolicy,
} from "aws-cdk-lib/aws-cloudfront";
import { S3BucketOrigin } from "aws-cdk-lib/aws-cloudfront-origins";
import { FunctionUrlAuthType, Runtime, Architecture, InvokeMode } from "aws-cdk-lib/aws-lambda";
import { NodejsFunction, OutputFormat } from "aws-cdk-lib/aws-lambda-nodejs";
import { RetentionDays } from "aws-cdk-lib/aws-logs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

export interface IdpStackProps extends StackProps {
  oracleConnectString: string;
  oracleUser: string;
  oraclePassword: string;
  oracleWalletLocation: string;
  oracleWalletPassword: string;
  ociUserOcid: string;
  ociTenancyOcid: string;
  ociCompartmentOcid: string;
  ociFingerprint: string;
  ociGenaiRegion: string;
  ociGenaiModel: string;
}

const LAMBDA_WALLET_PATH = "/var/task/wallet";

export class IdpStack extends Stack {
  constructor(scope: Construct, id: string, props: IdpStackProps) {
    super(scope, id, props);

    const apiFn = new NodejsFunction(this, "ApiFunction", {
      entry: join(ROOT, "services", "functions", "api", "src", "index.ts"),
      handler: "handler",
      runtime: Runtime.NODEJS_20_X,
      architecture: Architecture.ARM_64,
      memorySize: 1024,
      timeout: Duration.seconds(60),
      logRetention: RetentionDays.ONE_WEEK,
      bundling: {
        format: OutputFormat.ESM,
        target: "node20",
        minify: false,
        sourceMap: true,
        externalModules: ["oracledb"],
        nodeModules: ["oracledb"],
        mainFields: ["module", "main"],
        banner:
          "import { createRequire as topLevelCreateRequire } from 'module'; const require = topLevelCreateRequire(import.meta.url);",
        commandHooks: {
          beforeBundling: () => [],
          beforeInstall: () => [],
          afterBundling: (_inputDir: string, outputDir: string) => [
            `mkdir -p ${outputDir}/wallet`,
            `cp -R ${props.oracleWalletLocation}/. ${outputDir}/wallet/`,
          ],
        },
      },
      environment: {
        ORACLE_CONNECT_STRING: props.oracleConnectString,
        ORACLE_USER: props.oracleUser,
        ORACLE_PASSWORD: props.oraclePassword,
        ORACLE_WALLET_LOCATION: LAMBDA_WALLET_PATH,
        ORACLE_WALLET_PASSWORD: props.oracleWalletPassword,
        OCI_USER_OCID: props.ociUserOcid,
        OCI_TENANCY_OCID: props.ociTenancyOcid,
        OCI_COMPARTMENT_OCID: props.ociCompartmentOcid,
        OCI_FINGERPRINT: props.ociFingerprint,
        OCI_GENAI_REGION: props.ociGenaiRegion,
        OCI_GENAI_MODEL: props.ociGenaiModel,
        NODE_OPTIONS: "--enable-source-maps",
      },
    });

    const fnUrl = apiFn.addFunctionUrl({
      authType: FunctionUrlAuthType.NONE,
      invokeMode: InvokeMode.BUFFERED,
    });

    const siteBucket = new Bucket(this, "WebBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.S3_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const distribution = new Distribution(this, "WebDistribution", {
      defaultBehavior: {
        origin: S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachePolicy: CachePolicy.CACHING_OPTIMIZED,
        responseHeadersPolicy: ResponseHeadersPolicy.SECURITY_HEADERS,
      },
      defaultRootObject: "index.html",
      priceClass: PriceClass.PRICE_CLASS_100,
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: Duration.seconds(0),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: Duration.seconds(0),
        },
      ],
    });

    new CfnOutput(this, "ApiUrl", { value: fnUrl.url });
    new CfnOutput(this, "WebUrl", { value: `https://${distribution.distributionDomainName}` });
    new CfnOutput(this, "WebBucketName", { value: siteBucket.bucketName });
    new CfnOutput(this, "WebDistributionId", { value: distribution.distributionId });
  }
}

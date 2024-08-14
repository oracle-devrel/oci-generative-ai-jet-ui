import { ComponentProps } from "preact";
import { useEffect, useRef } from "preact/hooks";
import "oj-c/radioset";
import "oj-c/form-layout";
import "oj-c/select-single";
import { CRadiosetElement } from "oj-c/radioset";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");

type ServiceTypeVal = "text" | "summary" | "sim";
type BackendTypeVal = "java" | "python";
type Services = {
  label: string;
  value: ServiceTypeVal;
};
type Props = {
  aiServiceType: ServiceTypeVal;
  backendType: BackendTypeVal;
  aiServiceChange: (service: ServiceTypeVal) => void;
  backendChange: (backend: BackendTypeVal) => void;
  modelIdChange: (modelName: any) => void;
};

const serviceTypes = [
  { value: "text", label: "Generative Text" },
  { value: "summary", label: "Summarize" },
];
// { value: "sim", label: "Simulation" },

const backendTypes = [
  { value: "java", label: "Java" },
  { value: "python", label: "Python" },
];
const serviceOptionsDP = new MutableArrayDataProvider<
  Services["value"],
  Services
>(serviceTypes, { keyAttributes: "value" });
const backendOptionsDP = new MutableArrayDataProvider<
  Services["value"],
  Services
>(backendTypes, { keyAttributes: "value" });

export const Settings = (props: Props) => {
  const handleServiceTypeChange = (event: any) => {
    if (event.detail.updatedFrom === "internal")
      props.aiServiceChange(event.detail.value);
  };
  const handleBackendTypeChange = (event: any) => {
    if (event.detail.updatedFrom === "internal")
      props.backendChange(event.detail.value);
  };

  const modelDP = useRef(
    new MutableArrayDataProvider<string, {}>([], { keyAttributes: "id" })
  );

  const fetchModels = async () => {
    try {
      const response = await fetch("/api/genai/models");
      if (!response.ok) {
        throw new Error(`Response status: ${response.status}`);
      }
      const json = await response.json();
      modelDP.current.data = json;
    } catch (error: any) {
      console.log(
        "Java service not available for fetching list of Models: ",
        error.message
      );
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);
  return (
    <div class="oj-sm-margin-4x">
      <h2 class="oj-typography-heading-sm">AI service types</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="serviceTypeRadioset"
          value={props.aiServiceType}
          labelHint="AI service options"
          options={serviceOptionsDP}
          onvalueChanged={handleServiceTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
      <h2 class="oj-typography-heading-sm">Backend service types</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="backendTypeRadioset"
          value={props.backendType}
          labelHint="Backend options"
          options={backendOptionsDP}
          onvalueChanged={handleBackendTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
      {props.aiServiceType == "text" && props.backendType == "java" && (
        <>
          <h2 class="oj-typography-heading-sm">Model options</h2>
          <oj-c-form-layout>
            <oj-c-select-single
              data={modelDP.current}
              labelHint={"Model"}
              itemText={"name"}
              onvalueChanged={props.modelIdChange}
            ></oj-c-select-single>
          </oj-c-form-layout>
        </>
      )}
    </div>
  );
};

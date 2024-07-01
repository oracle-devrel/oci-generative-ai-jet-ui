import "preact";
import { useState } from "preact/hooks";
import "oj-c/radioset";
import "oj-c/form-layout";
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
};

const serviceTypes = [
  { value: "text", label: "Generative Text" },
  { value: "summary", label: "Summarize" },
  { value: "sim", label: "Simulation" },
];

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

  return (
    <div class="oj-sm-margin-4x">
      <h2 class="oj-typography-heading-sm">Service Settings</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="serviceTypeRadioset"
          value={props.aiServiceType}
          labelHint="AI Service Type"
          options={serviceOptionsDP}
          onvalueChanged={handleServiceTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
      <h2 class="oj-typography-heading-sm">Backend Service Type</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="backendTypeRadioset"
          value={props.backendType}
          labelHint="Backend Service Type"
          options={backendOptionsDP}
          onvalueChanged={handleBackendTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
    </div>
  );
};

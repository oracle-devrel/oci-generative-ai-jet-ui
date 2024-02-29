import "preact";
import { useState } from "preact/hooks";
import "oj-c/radioset";
import "oj-c/form-layout";
import { CRadiosetElement } from "oj-c/radioset";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");

type ServiceTypeVal = "text" | "summary" | "sim";
type Services = {
  label: string;
  value: ServiceTypeVal;
};
type Props = {
  serviceType: "text" | "summary" | "sim";
  serviceChange: (service: ServiceTypeVal) => void;
};

const serviceTypes = [
  { value: "text", label: "Generative Text" },
  { value: "summary", label: "Summarize" },
  { value: "sim", label: "Simulation" },
];
const serviceOptionsDP = new MutableArrayDataProvider<
  Services["value"],
  Services
>(serviceTypes, { keyAttributes: "value" });

export const Settings = (props: Props) => {
  const handleServiceTypeChange = (event: any) => {
    if (event.detail.updatedFrom === "internal")
      props.serviceChange(event.detail.value);
  };

  return (
    <div class="oj-sm-margin-4x">
      <h2 class="oj-typography-heading-sm">Service Settings</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="enabledRadioset"
          value={props.serviceType}
          labelHint="AI Service Type"
          options={serviceOptionsDP}
          onvalueChanged={handleServiceTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
    </div>
  );
};

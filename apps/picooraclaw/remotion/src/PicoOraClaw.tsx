import React from "react";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadSpaceMono } from "@remotion/google-fonts/SpaceMono";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";

import { TitleScene } from "./scenes/TitleScene";
import { NumbersScene } from "./scenes/NumbersScene";
import { WhyOracleScene } from "./scenes/WhyOracleScene";
import { ArchitectureScene } from "./scenes/ArchitectureScene";
import { AgentLoopScene } from "./scenes/AgentLoopScene";
import { ChannelsScene } from "./scenes/ChannelsScene";
import { ToolsScene } from "./scenes/ToolsScene";
import { HardwareToolsScene } from "./scenes/HardwareToolsScene";
import { ProvidersScene } from "./scenes/ProvidersScene";
import { OracleScene } from "./scenes/OracleScene";
import { VectorSearchScene } from "./scenes/VectorSearchScene";
import { OracleConfigScene } from "./scenes/OracleConfigScene";
import { SkillsSecurityScene } from "./scenes/SkillsSecurityScene";
import { InterfacesScene } from "./scenes/InterfacesScene";
import { QuickstartScene } from "./scenes/QuickstartScene";
import { CLICommandsScene } from "./scenes/CLICommandsScene";
import { InspectScene } from "./scenes/InspectScene";
import { DockerScene } from "./scenes/DockerScene";
import { OracleCloudScene } from "./scenes/OracleCloudScene";
import { DeployScene } from "./scenes/DeployScene";
import { EmbeddedTargetsScene } from "./scenes/EmbeddedTargetsScene";
import { VoiceCronScene } from "./scenes/VoiceCronScene";
import { UniqueScene } from "./scenes/UniqueScene";
import { SisterProjectsScene } from "./scenes/SisterProjectsScene";
import { OutroScene } from "./scenes/OutroScene";
import { SCENE_FRAMES, TRANSITION_FRAMES } from "./theme";

// Load fonts at module level
loadInter("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });
loadSpaceMono("normal", { weights: ["400", "700"], subsets: ["latin"] });

const T = TRANSITION_FRAMES;

export const PicoOraClaw: React.FC = () => {
  return (
    <TransitionSeries>
      {/* 1. Title */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.title}>
        <TitleScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 2. By The Numbers */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.numbers}>
        <NumbersScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 3. Why Oracle AI Database */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.whyOracle}>
        <WhyOracleScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 4. Architecture */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.architecture}>
        <ArchitectureScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-bottom" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 5. Agent Loop */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.agentLoop}>
        <AgentLoopScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={wipe()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 6. Channels */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.channels}>
        <ChannelsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 7. Tools */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.tools}>
        <ToolsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 8. Hardware Tools (I2C / SPI) */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.hardwareTools}>
        <HardwareToolsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 9. LLM Providers */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.providers}>
        <ProvidersScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-left" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 10. Oracle Integration */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.oracle}>
        <OracleScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 11. Vector Search */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.vectorSearch}>
        <VectorSearchScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={wipe()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 12. Oracle Config Reference */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.oracleConfig}>
        <OracleConfigScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 13. Skills & Security */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.skillsSecurity}>
        <SkillsSecurityScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-bottom" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 14. Go Interfaces */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.interfaces}>
        <InterfacesScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 15. Voice, Cron & Heartbeat */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.voiceCron}>
        <VoiceCronScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={wipe()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 16. Quickstart */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.quickstart}>
        <QuickstartScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 17. CLI Commands */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.cliCommands}>
        <CLICommandsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 18. Oracle Inspect */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.inspect}>
        <InspectScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-left" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 19. Docker & Compose */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.docker}>
        <DockerScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 20. Oracle Cloud Deploy */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.oracleCloud}>
        <OracleCloudScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={wipe()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 21. Deploy Targets */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.deploy}>
        <DeployScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-bottom" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 22. Embedded Targets */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.embeddedTargets}>
        <EmbeddedTargetsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 23. What Makes It Unique */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.unique}>
        <UniqueScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 24. Sister Projects */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.sisterProjects}>
        <SisterProjectsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      {/* 25. Outro / CTA */}
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES.outro}>
        <OutroScene />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};

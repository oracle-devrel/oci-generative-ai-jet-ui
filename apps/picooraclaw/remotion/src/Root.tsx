import React from "react";
import { Composition, Still, Folder } from "remotion";
import { PicoOraClaw } from "./PicoOraClaw";
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
import { VIDEO, SCENE_FRAMES, TRANSITION_FRAMES } from "./theme";

// Calculate total duration: sum of scenes - (transitions * transition_duration)
const TOTAL_SCENES = Object.values(SCENE_FRAMES).reduce((a, b) => a + b, 0);
const NUM_TRANSITIONS = Object.keys(SCENE_FRAMES).length - 1;
const TOTAL_DURATION = TOTAL_SCENES - NUM_TRANSITIONS * TRANSITION_FRAMES;

const W = VIDEO.width;
const H = VIDEO.height;
const FPS = VIDEO.fps;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Main showcase video */}
      <Composition
        id="PicoOraClawShowcase"
        component={PicoOraClaw}
        durationInFrames={TOTAL_DURATION}
        fps={FPS}
        width={W}
        height={H}
      />

      {/* Individual scenes for editor use */}
      <Folder name="Scenes">
        <Composition id="S01-Title" component={TitleScene} durationInFrames={SCENE_FRAMES.title} fps={FPS} width={W} height={H} />
        <Composition id="S02-Numbers" component={NumbersScene} durationInFrames={SCENE_FRAMES.numbers} fps={FPS} width={W} height={H} />
        <Composition id="S03-WhyOracle" component={WhyOracleScene} durationInFrames={SCENE_FRAMES.whyOracle} fps={FPS} width={W} height={H} />
        <Composition id="S04-Architecture" component={ArchitectureScene} durationInFrames={SCENE_FRAMES.architecture} fps={FPS} width={W} height={H} />
        <Composition id="S05-AgentLoop" component={AgentLoopScene} durationInFrames={SCENE_FRAMES.agentLoop} fps={FPS} width={W} height={H} />
        <Composition id="S06-Channels" component={ChannelsScene} durationInFrames={SCENE_FRAMES.channels} fps={FPS} width={W} height={H} />
        <Composition id="S07-Tools" component={ToolsScene} durationInFrames={SCENE_FRAMES.tools} fps={FPS} width={W} height={H} />
        <Composition id="S08-HardwareTools" component={HardwareToolsScene} durationInFrames={SCENE_FRAMES.hardwareTools} fps={FPS} width={W} height={H} />
        <Composition id="S09-Providers" component={ProvidersScene} durationInFrames={SCENE_FRAMES.providers} fps={FPS} width={W} height={H} />
        <Composition id="S10-Oracle" component={OracleScene} durationInFrames={SCENE_FRAMES.oracle} fps={FPS} width={W} height={H} />
        <Composition id="S11-VectorSearch" component={VectorSearchScene} durationInFrames={SCENE_FRAMES.vectorSearch} fps={FPS} width={W} height={H} />
        <Composition id="S12-OracleConfig" component={OracleConfigScene} durationInFrames={SCENE_FRAMES.oracleConfig} fps={FPS} width={W} height={H} />
        <Composition id="S13-SkillsSecurity" component={SkillsSecurityScene} durationInFrames={SCENE_FRAMES.skillsSecurity} fps={FPS} width={W} height={H} />
        <Composition id="S14-Interfaces" component={InterfacesScene} durationInFrames={SCENE_FRAMES.interfaces} fps={FPS} width={W} height={H} />
        <Composition id="S15-VoiceCron" component={VoiceCronScene} durationInFrames={SCENE_FRAMES.voiceCron} fps={FPS} width={W} height={H} />
        <Composition id="S16-Quickstart" component={QuickstartScene} durationInFrames={SCENE_FRAMES.quickstart} fps={FPS} width={W} height={H} />
        <Composition id="S17-CLICommands" component={CLICommandsScene} durationInFrames={SCENE_FRAMES.cliCommands} fps={FPS} width={W} height={H} />
        <Composition id="S18-Inspect" component={InspectScene} durationInFrames={SCENE_FRAMES.inspect} fps={FPS} width={W} height={H} />
        <Composition id="S19-Docker" component={DockerScene} durationInFrames={SCENE_FRAMES.docker} fps={FPS} width={W} height={H} />
        <Composition id="S20-OracleCloud" component={OracleCloudScene} durationInFrames={SCENE_FRAMES.oracleCloud} fps={FPS} width={W} height={H} />
        <Composition id="S21-Deploy" component={DeployScene} durationInFrames={SCENE_FRAMES.deploy} fps={FPS} width={W} height={H} />
        <Composition id="S22-EmbeddedTargets" component={EmbeddedTargetsScene} durationInFrames={SCENE_FRAMES.embeddedTargets} fps={FPS} width={W} height={H} />
        <Composition id="S23-Unique" component={UniqueScene} durationInFrames={SCENE_FRAMES.unique} fps={FPS} width={W} height={H} />
        <Composition id="S24-SisterProjects" component={SisterProjectsScene} durationInFrames={SCENE_FRAMES.sisterProjects} fps={FPS} width={W} height={H} />
        <Composition id="S25-Outro" component={OutroScene} durationInFrames={SCENE_FRAMES.outro} fps={FPS} width={W} height={H} />
      </Folder>

      {/* Thumbnail stills */}
      <Folder name="Stills">
        <Still id="Thumbnail-Title" component={TitleScene} width={W} height={H} />
        <Still id="Thumbnail-Oracle" component={OracleScene} width={W} height={H} />
      </Folder>
    </>
  );
};

package com.example.news.events.parser;

import java.util.List;
import java.util.regex.Pattern;

import com.example.news.events.parser.Splitter;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

public class SplitterTest {

    private final Pattern pattern = Pattern.compile("[.!?]");
    private final Splitter splitter = new Splitter(500, pattern);

    @Test
    void splitText() {
        final String text = "Atlanta (CNN)It was a scene worthy of any top cop show on TV -- bullets flying, banged-up cars and the FBI chasing an armed robbery suspect. In the end, two agents were injured in a crash and the suspect was shot before being captured. FBI agents and task force officers were following 36-year-old Kevone Charleston of Austell, Georgia, as he pulled into a CVS pharmacy in Forsyth County, Georgia, early Saturday. Charleston is suspected of involvement in 32 commercial robberies dating to November 2013, according to FBI officials. \"The incident all happened around 7 o'clock Saturday morning,\" said FBI Special Agent Stephen Emmett. \"There were multiple agents and officers that were following him based on his prior MO, and when they saw he was about to rob another CVS, they moved in.\" Authorities say Charleston parked his vehicle nearby and then popped the hood as if there were something wrong. Then he walked to the CVS, preparing to enter. When agents confronted him, Charleston ran, got in his car and traveled about 75 yards as agents opened fire. \"There were several FBI vehicles that were rammed or were hit by the suspect's vehicle when he was trying to flee. One government vehicle sustained heavy damage to its front and side, and another government SUV ended up on its side. That's how the two agents sustained their injuries,\" Emmett said. Twelve FBI agents and six government vehicles followed Charleston. Emmett said Charleston \"was trying to get away, our agents were trying to stop him. He collided with the first government vehicle, the Taurus, then the second, and the SUV ended on its side. \"The perp was stopped 8 feet away in the median, and that's where he received his gunshot wounds.\" The two agents were treated at an area hospital and released, according to Emmett, who says \"they are fine.\" Charleston was shot and wounded by FBI agents and task force officers, but his injuries are not life threatening, according to Forsyth County Sheriff's Deputy Robin Regan. Although he declined to give details of the 32 previous robberies, Emmett said it was an intensive investigation that was already underway as a priority for the FBI's violent crimes and major offender squad. He added, \"His MO involved armed confrontations, so our officers went into this fully prepared for an armed confrontation based on his past history.\" Emmett says he's relieved that the FBI's officers and agents are OK and that the suspect is in custody. He said it was the \"conclusion of an intensive and lengthy investigation.\" CNN's Vivian Kuo and Ryan Scallan contributed to this report.";
        List<String> chunks = splitter.split(text);
        assertThat(chunks.size()).isEqualTo(5);
    }
}

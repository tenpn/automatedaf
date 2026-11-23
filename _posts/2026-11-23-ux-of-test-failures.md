---
layout: post
title: "More is not always better: The UX of test failures"
categories: [Test Automation]
image: /images/blog/2026/chernobyl-control-room.jpg
date: 2026-11-23 00:00:00 +0000
newsletter_id: 204925014728770747
---

![The control room from HBO's Chernobyl. An overwhelming amount of lights and gauges and dials.](/images/blog/2026/chernobyl-control-room.jpg)

An automated test fails. The next step is the most important: how fast and how smoothly can you diagnose what's wrong?

I've seen enough studios now fighting uphill to get automation created and online, only to take no care about the user experience of a test failure. A Slack post mentions "test failures" but not which ones. A log-in to Jenkins later and you're now filtering lists and expanding trees to get to a test failure name - which is probably not super helpful. You're then opening logs and ctrl-F'ing for error statements, or, worse, scrubbing videos.

And when there's not enough information, it's too easy to default to adding more logging, screenshots, artifacts, instead of smartly surfacing what's there.

At your next failure, don't throw more fuel on the fire. Instead, stop, take a breath, and follow these three steps:

## Step 1: Chop

The biggest crime I see with test failures is a test that's doing too much. A failure in the "Complete Level" test tells you very little about what might have happened. Did the gems stop spawning? Did the score system break? Did a piece of geo have the wrong physics layer?

Much better to break down big long tests into tests with just one or two asserts in them. In long [smoke tests]({% post_url 2025-09-03-theres-no-fire-without-smoke-tests %}), this sometimes requires some jiggery-pokery with smaller fixtures, allowing more fine-grained setup/teardown, but don't forget OneTimeSetUp and OneTimeTearDown are valuable tools too.

For smoke tests, this is the one time it's acceptable to have ordering and dependency between your tests. It's also a good time to update your naming convention so your test names are as informative as possible. I like Given_When_Then for this, where Given is the context, When is the action and Then is the assert.

The end result should be seeing a GivenObjective_WhenCompleted_ThenGemsSpawn test fail. That tells you way more already about what went wrong.

## Step 2: Capture

What's most useful to diagnose the problem? Alongside the test name, any errors, and the context surrounding them. Use regex to filter noise and capture just the errors. Grep and other tools allow fetching lines _around_ a match along with the match, or you could use capture groups or bounded wildcards.

Don't just do a grab bag: the current level, character stats, purchased IAPs, inventory, world position, score, all _might_ be useful information, but until you see a failure that needs one of them, don't add them. This keeps the captures focused and valuable. "This might be useful in the future" is how test failures become overwhelming.

## Step 3: Convey

It's no good if all this useful info is fifteen layers deep in Jenkins. You want the team to be proactive about fixing failures, rather than relying on you to collate and tag everyone. Take the captured info and the test name, and put it in a thread under a brief Slack post.

The ideal should be that people are able to see a test failure, read the thread, and go to fix the problem without ever opening the CI/CD pipeline.

This probably requires some customisation of your server. TeamCity is particularly bad at giving you fine-grained control of Slack posting, leading to firehoses of easily-ignorable noise. If you'd like me to come take a look at your setup, reach out at [automatedaf.dev](https://automatedaf.dev).

## Actionable Tests

This becomes muscle memory - it's very easy to tip one way or the other, having too much info in your failures or not enough. There are few shortcuts, but practice remains the best advice. Try some stuff, wait for a failure, and react. If possible, speak to those processing the test failures and ask them what they found useful. Refine and iterate over time, just like making a game.

Some readers at this point might be thinking what if they could throw an agent at the problem: that's definitely an option, and one I've implemented for some clients. But even then, your agent will work faster and consume fewer tokens if you do these steps too.

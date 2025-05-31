# Score Calculation in DesiQ

This document explains how various scores and metrics are calculated in the DesiQ application.

## User Scores

### Skill Scores

DesiQ tracks four main skill scores for each user:

1. **Rationality Score (0-100)**: Measures your ability to make logical, evidence-based decisions
   - Increases when you choose scenario options that demonstrate good reasoning and critical thinking
   - Decreases with choices that show illogical or irrational thinking
   - Formula: Accumulation of rationality_points from each completed scenario option

2. **Decisiveness Score (0-100)**: Evaluates your ability to make confident and timely decisions
   - Increases with choices that show clear decision-making without unnecessary delay
   - Decreases with indecisive or overly cautious choices when quick action is needed
   - Formula: Accumulation of decisiveness_points from each completed scenario option

3. **Empathy Score (0-100)**: Measures your ability to understand and consider others' perspectives
   - Increases with choices that demonstrate care for others' feelings and needs
   - Decreases with self-centered choices that ignore the impact on others
   - Formula: Accumulation of empathy_points from each completed scenario option

4. **Clarity Score (0-100)**: Assesses your ability to see the complete picture and understand context
   - Increases with choices that show full comprehension of the situation
   - Decreases with choices that miss key details or misinterpret information
   - Formula: Accumulation of clarity_points from each completed scenario option

All scores are capped at 100 and cannot go below 0.

### Level and XP System

- **XP (Experience Points)**: Gained by completing scenarios, daily challenges, and other activities
  - Each scenario completion awards XP based on its difficulty (typically 10-30 XP)
  - Daily challenges provide additional XP rewards
  - Personality tests award 20 XP upon completion

- **Level**: Determined by your total XP
  - Formula: `Level = (XP ÷ 100) + 1`
  - Each level requires 100 XP
  - Higher levels unlock new scenarios, personality tests, and features

- **XP Progress**: Shows your progress toward the next level
  - Formula: `Progress % = ((XP - (Level-1)*100) ÷ 100) × 100`

### Streak System

- **Daily Streak**: The number of consecutive days you've engaged with the platform
  - Increments by 1 for each consecutive day you log in
  - Resets to 0 if you miss a day
  - Tracked via the `last_login_date` field in your profile

## Scenario Scoring

When you complete a scenario by selecting an option:

1. The option's skill points are added to your profile scores
2. You receive the scenario's XP reward
3. Your level is updated based on new total XP
4. The scenario is marked as completed

Each scenario option has the following point values:
- Rationality points (0-10)
- Decisiveness points (0-10)
- Empathy points (0-10)
- Clarity points (0-10)

The total score for a scenario choice is the sum of these four values (max 40).

## Activity Score (for Leaderboards)

Your activity score determines your ranking among other users:

```
Activity Score = XP Points + (Daily Streak × 10) + (Scenarios Completed × 5) + 
                (Comments × 2) + (Likes Received × 1) + (Posts × 3)
```

Higher activity scores result in higher rankings on the leaderboard. 
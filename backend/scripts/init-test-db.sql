-- Separate database for pytest so test runs (which TRUNCATE tables) never touch dev data.
CREATE DATABASE lead_intake_test OWNER lead_intake;

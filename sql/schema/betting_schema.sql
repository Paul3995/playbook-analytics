-- ============================================================
-- Sporty Analytics — Core Betting Platform Schema (MySQL)
-- ============================================================

CREATE DATABASE IF NOT EXISTS sporty;
USE sporty;

-- Players / user accounts
CREATE TABLE IF NOT EXISTS users (
    user_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(80)     NOT NULL UNIQUE,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    country_code    CHAR(2)         NOT NULL,
    currency        CHAR(3)         NOT NULL DEFAULT 'USD',
    registration_ts DATETIME        NOT NULL,
    first_deposit_ts DATETIME,
    last_login_ts   DATETIME,
    status          ENUM('active','suspended','closed') NOT NULL DEFAULT 'active',
    vip_tier        ENUM('bronze','silver','gold','platinum') DEFAULT 'bronze',
    INDEX idx_country   (country_code),
    INDEX idx_reg_ts    (registration_ts),
    INDEX idx_status    (status)
) ENGINE=InnoDB;

-- Sports & competitions
CREATE TABLE IF NOT EXISTS sports (
    sport_id    SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,
    slug        VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS competitions (
    competition_id  SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sport_id        SMALLINT UNSIGNED NOT NULL,
    name            VARCHAR(100) NOT NULL,
    country_code    CHAR(2),
    FOREIGN KEY (sport_id) REFERENCES sports(sport_id)
) ENGINE=InnoDB;

-- Events (matches)
CREATE TABLE IF NOT EXISTS events (
    event_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    competition_id  SMALLINT UNSIGNED NOT NULL,
    home_team       VARCHAR(100) NOT NULL,
    away_team       VARCHAR(100) NOT NULL,
    scheduled_start DATETIME    NOT NULL,
    actual_start    DATETIME,
    status          ENUM('prematch','live','suspended','settled','cancelled') NOT NULL DEFAULT 'prematch',
    result          VARCHAR(20),                 -- e.g. "2-1"
    INDEX idx_status        (status),
    INDEX idx_scheduled     (scheduled_start),
    FOREIGN KEY (competition_id) REFERENCES competitions(competition_id)
) ENGINE=InnoDB;

-- Markets (e.g. "Match Result", "Total Goals Over/Under")
CREATE TABLE IF NOT EXISTS markets (
    market_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id    BIGINT UNSIGNED NOT NULL,
    market_type VARCHAR(80)  NOT NULL,   -- '1X2', 'BTTS', 'TOTAL_GOALS', 'ASIAN_HANDICAP'
    status      ENUM('open','suspended','settled','cancelled') NOT NULL DEFAULT 'open',
    result_key  VARCHAR(50),             -- winning selection key after settlement
    INDEX idx_event (event_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id)
) ENGINE=InnoDB;

-- Selections (individual odds within a market)
CREATE TABLE IF NOT EXISTS selections (
    selection_id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    market_id       BIGINT UNSIGNED NOT NULL,
    name            VARCHAR(80)  NOT NULL,   -- 'Home', 'Draw', 'Away', 'Over 2.5'
    odds            DECIMAL(8,3) NOT NULL,
    result          ENUM('win','lose','void') DEFAULT NULL,
    INDEX idx_market (market_id),
    FOREIGN KEY (market_id) REFERENCES markets(market_id)
) ENGINE=InnoDB;

-- Bets placed by users
CREATE TABLE IF NOT EXISTS bets (
    bet_id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL,
    bet_type        ENUM('single','accumulator','system') NOT NULL DEFAULT 'single',
    stake           DECIMAL(12,2)   NOT NULL,
    potential_payout DECIMAL(12,2)  NOT NULL,
    actual_payout   DECIMAL(12,2)   DEFAULT NULL,
    status          ENUM('pending','won','lost','void','cashed_out') NOT NULL DEFAULT 'pending',
    placed_ts       DATETIME        NOT NULL,
    settled_ts      DATETIME        DEFAULT NULL,
    currency        CHAR(3)         NOT NULL DEFAULT 'USD',
    INDEX idx_user_id   (user_id),
    INDEX idx_placed_ts (placed_ts),
    INDEX idx_status    (status),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

-- Junction: selections within a bet (supports accumulators)
CREATE TABLE IF NOT EXISTS bet_selections (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bet_id          BIGINT UNSIGNED NOT NULL,
    selection_id    BIGINT UNSIGNED NOT NULL,
    odds_at_place   DECIMAL(8,3)    NOT NULL,
    UNIQUE KEY uq_bet_sel (bet_id, selection_id),
    FOREIGN KEY (bet_id)       REFERENCES bets(bet_id),
    FOREIGN KEY (selection_id) REFERENCES selections(selection_id)
) ENGINE=InnoDB;

-- Financial transactions (deposits / withdrawals / bonuses)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL,
    type            ENUM('deposit','withdrawal','bonus','adjustment') NOT NULL,
    amount          DECIMAL(12,2)   NOT NULL,
    currency        CHAR(3)         NOT NULL DEFAULT 'USD',
    status          ENUM('pending','completed','failed','reversed') NOT NULL DEFAULT 'pending',
    created_ts      DATETIME        NOT NULL,
    completed_ts    DATETIME        DEFAULT NULL,
    payment_method  VARCHAR(50),
    reference       VARCHAR(100),
    INDEX idx_user_ts   (user_id, created_ts),
    INDEX idx_type      (type),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

-- A/B test experiment registry
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL UNIQUE,
    description     TEXT,
    hypothesis      TEXT,
    metric          VARCHAR(80)     NOT NULL,   -- primary metric being tested
    status          ENUM('draft','running','paused','completed') NOT NULL DEFAULT 'draft',
    start_ts        DATETIME,
    end_ts          DATETIME,
    min_sample_size INT UNSIGNED,
    created_ts      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Assignment of users to experiment variants
CREATE TABLE IF NOT EXISTS experiment_assignments (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    experiment_id   INT UNSIGNED    NOT NULL,
    user_id         BIGINT UNSIGNED NOT NULL,
    variant         ENUM('control','treatment') NOT NULL,
    assigned_ts     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_exp_user (experiment_id, user_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
    FOREIGN KEY (user_id)       REFERENCES users(user_id)
) ENGINE=InnoDB;

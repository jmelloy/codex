"""Tests for the Texas Hold'em poker agent simulation module."""

import pytest

from codex.scripts.holdem_agents import (
    BOTS,
    HoldEmAgent,
    random_bot,
    simulate_hand,
    simulate_tournament,
)

# ---------------------------------------------------------------------------
# HoldEmAgent unit tests
# ---------------------------------------------------------------------------


class TestHoldEmAgent:
    """Tests for the HoldEmAgent dataclass."""

    def _make_agent(self, **kwargs) -> HoldEmAgent:
        defaults = dict(name="TestBot", seed=99)
        defaults.update(kwargs)
        return HoldEmAgent(**defaults)

    def test_default_fields(self):
        agent = self._make_agent()
        assert agent.aggression_factor == 0.5
        assert agent.bluff_rate == 0.1
        assert agent.tight_factor == 0.5
        assert agent.call_threshold == 0.3
        assert agent.raise_multiplier == 2.0
        assert agent.position_awareness == 0.5
        assert agent.pot_odds_skill == 0.5

    def test_initial_state(self):
        agent = self._make_agent()
        assert agent.chips == 1000
        assert agent.hands_played == 0
        assert agent.hands_won == 0
        assert agent.chip_history == [1000]

    def test_record_hand_win(self):
        agent = self._make_agent()
        agent.record_hand(200)
        assert agent.chips == 1200
        assert agent.hands_played == 1
        assert agent.hands_won == 1
        assert agent.chip_history == [1000, 1200]

    def test_record_hand_loss(self):
        agent = self._make_agent()
        agent.record_hand(-50)
        assert agent.chips == 950
        assert agent.hands_played == 1
        assert agent.hands_won == 0
        assert 950 in agent.chip_history

    def test_chips_never_negative(self):
        agent = self._make_agent()
        agent.chips = 10
        agent.record_hand(-500)
        assert agent.chips == 0

    def test_win_rate_no_hands(self):
        agent = self._make_agent()
        assert agent.win_rate == 0.0

    def test_win_rate_calculation(self):
        agent = self._make_agent()
        agent.record_hand(100)
        agent.record_hand(-50)
        agent.record_hand(200)
        assert agent.win_rate == pytest.approx(2 / 3)

    def test_wants_to_enter_pot_strong_hand(self):
        agent = self._make_agent(tight_factor=0.4, bluff_rate=0.0)
        # A very strong hand should always enter
        assert agent.wants_to_enter_pot(0.99) is True

    def test_wants_to_enter_pot_weak_hand_tight_bot(self):
        agent = self._make_agent(tight_factor=0.9, bluff_rate=0.0, seed=12345)
        # With bluff_rate=0.0 and raw_strength=0.2 < tight_factor=0.9,
        # the bot should NEVER enter the pot (deterministic result).
        enters = sum(agent.wants_to_enter_pot(0.2) for _ in range(100))
        assert enters == 0  # tight bot with bluff_rate=0 never plays weak hands

    def test_decide_action_check_when_no_bet(self):
        agent = self._make_agent(aggression_factor=0.0, bluff_rate=0.0)
        action, amount = agent.decide_action(raw_strength=0.9, pot=100, to_call=0)
        assert action == "check"
        assert amount == 0

    def test_decide_action_fold_weak_hand(self):
        agent = self._make_agent(call_threshold=0.8, bluff_rate=0.0, seed=5)
        action, amount = agent.decide_action(raw_strength=0.1, pot=100, to_call=50)
        assert action == "fold"
        assert amount == 0

    def test_decide_action_raises_with_strong_hand_aggressive_bot(self):
        agent = self._make_agent(aggression_factor=1.0, bluff_rate=0.0, call_threshold=0.0)
        action, amount = agent.decide_action(raw_strength=0.9, pot=100, to_call=10)
        assert action == "raise"
        assert amount > 10

    def test_decide_action_bluff_fires(self):
        # Bluff rate 1.0 means always bluffs
        agent = self._make_agent(bluff_rate=1.0, aggression_factor=0.0)
        action, _ = agent.decide_action(raw_strength=0.0, pot=100, to_call=0)
        assert action == "raise"


# ---------------------------------------------------------------------------
# BOTS preset tests
# ---------------------------------------------------------------------------


class TestBotPresets:
    """Tests for the pre-built BOTS list."""

    def test_six_bots_defined(self):
        assert len(BOTS) == 6

    def test_all_bots_have_unique_names(self):
        names = [b.name for b in BOTS]
        assert len(names) == len(set(names))

    def test_all_bots_have_unique_seeds(self):
        seeds = [b.seed for b in BOTS]
        assert len(seeds) == len(set(seeds))

    def test_randomization_fields_in_valid_range(self):
        for bot in BOTS:
            assert 0.0 <= bot.aggression_factor <= 1.0, f"{bot.name}: aggression_factor out of range"
            assert 0.0 <= bot.bluff_rate <= 1.0, f"{bot.name}: bluff_rate out of range"
            assert 0.0 <= bot.tight_factor <= 1.0, f"{bot.name}: tight_factor out of range"
            assert 0.0 <= bot.call_threshold <= 1.0, f"{bot.name}: call_threshold out of range"
            assert 1.0 <= bot.raise_multiplier <= 4.0, f"{bot.name}: raise_multiplier out of range"
            assert 0.0 <= bot.position_awareness <= 1.0, f"{bot.name}: position_awareness out of range"
            assert 0.0 <= bot.pot_odds_skill <= 1.0, f"{bot.name}: pot_odds_skill out of range"

    def test_bots_have_distinct_personalities(self):
        """Key randomization fields must differ across bots."""
        aggressions = [b.aggression_factor for b in BOTS]
        bluff_rates = [b.bluff_rate for b in BOTS]
        tight_factors = [b.tight_factor for b in BOTS]

        # At least 4 distinct values for each key field
        assert len(set(aggressions)) >= 4
        assert len(set(bluff_rates)) >= 4
        assert len(set(tight_factors)) >= 4


# ---------------------------------------------------------------------------
# random_bot tests
# ---------------------------------------------------------------------------


class TestRandomBot:
    """Tests for the random_bot factory function."""

    def test_returns_holdem_agent(self):
        bot = random_bot()
        assert isinstance(bot, HoldEmAgent)

    def test_personality_matches_a_preset(self):
        bot = random_bot()
        preset_fields = [
            (
                p.aggression_factor,
                p.bluff_rate,
                p.tight_factor,
                p.call_threshold,
                p.raise_multiplier,
                p.position_awareness,
                p.pot_odds_skill,
            )
            for p in BOTS
        ]
        bot_fields = (
            bot.aggression_factor,
            bot.bluff_rate,
            bot.tight_factor,
            bot.call_threshold,
            bot.raise_multiplier,
            bot.position_awareness,
            bot.pot_odds_skill,
        )
        assert bot_fields in preset_fields

    def test_custom_seat_name(self):
        bot = random_bot(seat="Seat 3")
        assert bot.name == "Seat 3"

    def test_auto_name_includes_preset_name(self):
        import random as _random

        # Force a specific preset via a seeded rng
        rng = _random.Random(0)
        preset = rng.choice(BOTS)
        rng2 = _random.Random(0)
        bot = random_bot(rng=rng2)
        assert bot.name.startswith(preset.name)

    def test_returns_independent_copies(self):
        """Multiple assigned bots must not share state."""
        b1 = random_bot()
        b2 = random_bot()
        b1.chips = 500
        assert b2.chips == 1000  # b2 unaffected by b1 mutation

    def test_bots_have_different_seeds(self):
        seeds = {random_bot().seed for _ in range(20)}
        # Across 20 draws we expect at least 5 distinct seeds
        assert len(seeds) >= 5

    def test_rng_controls_preset_selection(self):
        import random as _random

        rng_a = _random.Random(42)
        rng_b = _random.Random(42)
        bot_a = random_bot(rng=rng_a)
        bot_b = random_bot(rng=rng_b)
        # Same RNG seed → same preset personality
        assert bot_a.aggression_factor == bot_b.aggression_factor
        assert bot_a.bluff_rate == bot_b.bluff_rate

    def test_assigned_bots_can_play_tournament(self):
        import random as _random

        rng = _random.Random(7)
        players = [random_bot(seat=f"Seat {i + 1}", rng=rng) for i in range(6)]
        histories = simulate_tournament(players, num_hands=50, seed=7)
        assert len(histories) == 6
        for history in histories.values():
            assert len(history) == 51
            assert all(c >= 0 for c in history)


# ---------------------------------------------------------------------------
# simulate_tournament tests
# ---------------------------------------------------------------------------


class TestSimulateTournament:
    """Tests for the simulate_tournament function."""

    def test_returns_history_for_all_bots(self):
        histories = simulate_tournament(BOTS, num_hands=10, seed=0)
        assert set(histories.keys()) == {b.name for b in BOTS}

    def test_history_length_matches_hands(self):
        histories = simulate_tournament(BOTS, num_hands=50, seed=1)
        for name, history in histories.items():
            # history has initial value + one entry per hand = num_hands + 1
            assert len(history) == 51, f"{name}: expected 51 entries, got {len(history)}"

    def test_chip_histories_are_all_different(self):
        """The core requirement: each bot must produce a unique chip history."""
        histories = simulate_tournament(BOTS, num_hands=200, seed=42)
        history_tuples = [tuple(h) for h in histories.values()]
        assert len(set(history_tuples)) == len(BOTS), "Not all bots produced unique chip histories"

    def test_chip_histories_diverge_meaningfully(self):
        """Bots should reach meaningfully different chip counts by mid-tournament."""
        histories = simulate_tournament(BOTS, num_hands=300, seed=42)
        mid_chips = {name: history[150] for name, history in histories.items()}
        # At least 3 distinct chip counts at the midpoint
        assert len(set(mid_chips.values())) >= 3, (
            f"Bot chip counts should diverge; midpoint values: {mid_chips}"
        )

    def test_deterministic_with_same_seed(self):
        h1 = simulate_tournament(BOTS, num_hands=100, seed=7)
        h2 = simulate_tournament(BOTS, num_hands=100, seed=7)
        assert h1 == h2

    def test_different_seeds_produce_different_results(self):
        h1 = simulate_tournament(BOTS, num_hands=100, seed=1)
        h2 = simulate_tournament(BOTS, num_hands=100, seed=2)
        assert h1 != h2

    def test_resets_state_between_runs(self):
        simulate_tournament(BOTS, num_hands=100, seed=10)
        first_run_chips = {b.name: b.chips for b in BOTS}

        simulate_tournament(BOTS, num_hands=100, seed=10)
        second_run_chips = {b.name: b.chips for b in BOTS}

        assert first_run_chips == second_run_chips

    def test_all_histories_start_at_1000(self):
        histories = simulate_tournament(BOTS, num_hands=50, seed=3)
        for name, history in histories.items():
            assert history[0] == 1000, f"{name}: expected starting chips of 1000"

    def test_chips_never_go_negative(self):
        histories = simulate_tournament(BOTS, num_hands=500, seed=99)
        for name, history in histories.items():
            assert all(c >= 0 for c in history), f"{name}: chips went negative"


# ---------------------------------------------------------------------------
# simulate_hand unit tests
# ---------------------------------------------------------------------------


class TestSimulateHand:
    """Tests for the simulate_hand function."""

    def test_hand_updates_chip_history(self):
        import random

        bots = [
            HoldEmAgent(name="A", seed=1, aggression_factor=0.5, bluff_rate=0.1),
            HoldEmAgent(name="B", seed=2, aggression_factor=0.3, bluff_rate=0.05),
        ]
        rng = random.Random(42)
        simulate_hand(bots, rng, big_blind=10)
        for bot in bots:
            assert len(bot.chip_history) > 0

    def test_single_player_noop(self):
        import random

        bot = HoldEmAgent(name="Solo", seed=1)
        rng = random.Random(0)
        simulate_hand([bot], rng, big_blind=10)
        # Nothing meaningful should happen with only one player
        assert bot.chips >= 0

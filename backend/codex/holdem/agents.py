"""Texas Hold'em poker agent bots with randomized strategy parameters.

Each bot is initialized with different randomization field values so that
when simulated, they exhibit distinct playing styles and performance curves
(chip histories over time).

Randomization fields
--------------------
aggression_factor : float  [0.0 – 1.0]
    Tendency to bet / raise rather than check / call.
bluff_rate : float  [0.0 – 1.0]
    Probability of betting with a weak hand.
tight_factor : float  [0.0 – 1.0]
    Minimum hand-strength quantile required to enter a pot.
    High values mean only premium hands are played.
call_threshold : float  [0.0 – 1.0]
    Minimum hand strength needed to call an opponent's bet.
raise_multiplier : float  [1.0 – 4.0]
    Bet size expressed as a multiple of the big blind.
position_awareness : float  [0.0 – 1.0]
    How strongly the bot adjusts strategy based on table position.
pot_odds_skill : float  [0.0 – 1.0]
    Accuracy of implied-odds calculations when deciding to call / fold.

Usage
-----
    from codex.holdem.agents import BOTS, random_bot, simulate_tournament, plot_results

    # Assign a randomly-chosen preset to each seat in a game:
    players = [random_bot() for _ in range(6)]

    histories = simulate_tournament(players, num_hands=500, seed=42)
    plot_results(histories)           # requires matplotlib
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------


@dataclass
class HoldEmAgent:
    """Texas Hold'em poker agent with randomizable strategy parameters."""

    name: str
    seed: int

    # ------------------------------------------------------------------
    # Randomization fields – these drive the bot's personality and make
    # each bot's chip-history curve look different when plotted.
    # ------------------------------------------------------------------
    aggression_factor: float = 0.5
    """0.0 = very passive (checks/calls only); 1.0 = very aggressive (bets/raises always)."""

    bluff_rate: float = 0.1
    """Probability of making a continuation-bet or bluff with a weak hand."""

    tight_factor: float = 0.5
    """Minimum normalized hand strength needed to voluntarily enter the pot."""

    call_threshold: float = 0.3
    """Minimum hand strength required to call a bet (0.0 = call anything, 1.0 = almost never call)."""

    raise_multiplier: float = 2.0
    """Bet / raise size as a multiple of the pot; clamped to [1.0, 4.0]."""

    position_awareness: float = 0.5
    """Bonus applied to effective hand strength when acting in late position."""

    pot_odds_skill: float = 0.5
    """How accurately the bot evaluates pot-odds; 0 = random, 1 = perfect."""

    # ------------------------------------------------------------------
    # Runtime state (reset per simulation)
    # ------------------------------------------------------------------
    chips: int = field(default=1000, repr=False)
    hands_played: int = field(default=0, repr=False)
    hands_won: int = field(default=0, repr=False)
    total_invested: int = field(default=0, repr=False)
    chip_history: list[int] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.chip_history = [self.chips]

    # ------------------------------------------------------------------
    # Decision helpers
    # ------------------------------------------------------------------

    def _effective_strength(self, raw_strength: float, position_bonus: float) -> float:
        """Adjust raw hand strength by position awareness."""
        return min(1.0, raw_strength + position_bonus * self.position_awareness)

    def wants_to_enter_pot(self, raw_strength: float, position_bonus: float = 0.0) -> bool:
        """Return True if the bot will voluntarily enter the pot pre-flop."""
        eff = self._effective_strength(raw_strength, position_bonus)
        # Tight bots require stronger hands; bluffers sometimes enter with weak hands
        bluffing = self._rng.random() < self.bluff_rate
        return bluffing or (eff >= self.tight_factor)

    def decide_action(
        self,
        raw_strength: float,
        pot: int,
        to_call: int,
        position_bonus: float = 0.0,
    ) -> tuple[str, int]:
        """Return (action, amount).

        Actions
        -------
        "fold"  – forfeit the hand
        "call"  – match the bet (amount = to_call)
        "raise" – increase the bet (amount = raise size)
        "check" – no bet required, pass action (amount = 0)
        """
        eff = self._effective_strength(raw_strength, position_bonus)

        # Bluff override – bet regardless of hand strength
        if self._rng.random() < self.bluff_rate:
            bet = max(1, int(pot * self.raise_multiplier))
            return ("raise", bet)

        if to_call == 0:
            # No bet to call – check or bet
            if self._rng.random() < self.aggression_factor and eff >= 0.3:
                bet = max(1, int(pot * self.raise_multiplier))
                return ("raise", bet)
            return ("check", 0)

        # Pot-odds adjustment: good players know when to call even weak hands
        pot_odds_adjustment = (1.0 - self.pot_odds_skill) * self._rng.uniform(-0.15, 0.15)
        adjusted_threshold = max(0.0, self.call_threshold + pot_odds_adjustment)

        if eff < adjusted_threshold:
            return ("fold", 0)

        # Strong enough to raise?
        if self._rng.random() < self.aggression_factor and eff >= 0.55:
            bet = max(to_call + 1, int(pot * self.raise_multiplier))
            return ("raise", bet)

        return ("call", to_call)

    def record_hand(self, net_gain: int) -> None:
        """Update state after a hand completes."""
        self.chips = max(0, self.chips + net_gain)
        self.hands_played += 1
        if net_gain > 0:
            self.hands_won += 1
        self.chip_history.append(self.chips)

    @property
    def win_rate(self) -> float:
        if self.hands_played == 0:
            return 0.0
        return self.hands_won / self.hands_played


# ---------------------------------------------------------------------------
# Pre-built bots – each initialised with distinct randomization values
# ---------------------------------------------------------------------------

BOTS: list[HoldEmAgent] = [
    HoldEmAgent(
        name="Rock",
        seed=1001,
        aggression_factor=0.15,   # passive
        bluff_rate=0.03,           # rarely bluffs
        tight_factor=0.75,         # only premium hands
        call_threshold=0.60,       # needs strong hand to call
        raise_multiplier=2.5,      # moderate raise size
        position_awareness=0.40,
        pot_odds_skill=0.55,
    ),
    HoldEmAgent(
        name="Maniac",
        seed=1002,
        aggression_factor=0.90,   # hyper-aggressive
        bluff_rate=0.45,           # bluffs constantly
        tight_factor=0.10,         # plays almost any hand
        call_threshold=0.05,       # calls almost everything
        raise_multiplier=3.5,      # huge raises
        position_awareness=0.20,   # ignores position
        pot_odds_skill=0.15,       # poor pot-odds reads
    ),
    HoldEmAgent(
        name="Shark",
        seed=1003,
        aggression_factor=0.70,   # aggressive but selective
        bluff_rate=0.18,           # bluffs moderately
        tight_factor=0.55,         # plays good hands
        call_threshold=0.35,       # calls with decent hands
        raise_multiplier=2.8,      # above-average raise size
        position_awareness=0.85,   # highly position-aware
        pot_odds_skill=0.90,       # excellent pot-odds reader
    ),
    HoldEmAgent(
        name="Fish",
        seed=1004,
        aggression_factor=0.25,   # mostly passive
        bluff_rate=0.05,           # rarely bluffs
        tight_factor=0.20,         # plays most hands (loose)
        call_threshold=0.10,       # almost always calls
        raise_multiplier=1.5,      # small raises
        position_awareness=0.10,   # no position awareness
        pot_odds_skill=0.10,       # poor pot-odds judgment
    ),
    HoldEmAgent(
        name="Nit",
        seed=1005,
        aggression_factor=0.10,   # extremely passive
        bluff_rate=0.01,           # almost never bluffs
        tight_factor=0.90,         # only the very best hands
        call_threshold=0.80,       # almost never calls without the nuts
        raise_multiplier=2.0,      # standard raise size
        position_awareness=0.60,
        pot_odds_skill=0.70,
    ),
    HoldEmAgent(
        name="LAG",
        seed=1006,
        aggression_factor=0.80,   # loose-aggressive
        bluff_rate=0.30,           # frequent bluffs
        tight_factor=0.25,         # wide range of hands
        call_threshold=0.20,       # calls a lot
        raise_multiplier=3.0,      # large raises
        position_awareness=0.75,   # very position-aware
        pot_odds_skill=0.65,       # reasonable pot-odds skill
    ),
]


# ---------------------------------------------------------------------------
# Bot assignment helper
# ---------------------------------------------------------------------------

_bot_counter = 0  # global counter for generating unique seat names


def random_bot(seat: str | None = None, rng: random.Random | None = None) -> HoldEmAgent:
    """Return a fresh :class:`HoldEmAgent` whose personality is randomly
    chosen from the pre-built :data:`BOTS` presets.

    Each call returns an *independent* copy so that multiple bots assigned
    to the same game do not share state with each other or with the originals
    in :data:`BOTS`.

    Parameters
    ----------
    seat:
        An optional display name for this bot instance (e.g. ``"Seat 1"``).
        When omitted an auto-generated name like ``"Rock-1"`` is used.
    rng:
        Optional :class:`random.Random` instance used to pick the preset.
        Passing the same ``rng`` lets callers control which preset is chosen.
        When omitted, ``random.Random()`` is used (non-deterministic).

    Returns
    -------
    A new :class:`HoldEmAgent` initialised with the chosen preset's
    randomization fields, a fresh seed, and a unique starting chip count.

    Examples
    --------
    Seat six players with randomly chosen strategies::

        players = [random_bot(seat=f"Seat {i+1}") for i in range(6)]
        histories = simulate_tournament(players, num_hands=300)
    """
    global _bot_counter

    picker = rng if rng is not None else random.Random()
    preset = picker.choice(BOTS)

    _bot_counter += 1
    name = seat if seat is not None else f"{preset.name}-{_bot_counter}"

    # Each assigned bot gets its own unique seed so its internal RNG is
    # independent from both the preset and any other assigned bots.
    unique_seed = hash((preset.seed, _bot_counter)) & 0xFFFF_FFFF

    return HoldEmAgent(
        name=name,
        seed=unique_seed,
        aggression_factor=preset.aggression_factor,
        bluff_rate=preset.bluff_rate,
        tight_factor=preset.tight_factor,
        call_threshold=preset.call_threshold,
        raise_multiplier=preset.raise_multiplier,
        position_awareness=preset.position_awareness,
        pot_odds_skill=preset.pot_odds_skill,
    )


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def simulate_hand(
    players: Sequence[HoldEmAgent],
    rng: random.Random,
    big_blind: int = 10,
) -> None:
    """Simulate one hand of Texas Hold'em among all players.

    This is a simplified (but statistically meaningful) model:
    - Each player receives a random hand-strength (uniform 0–1).
    - Pre-flop: players decide whether to enter the pot.
    - Post-flop: one round of betting among those who entered.
    - The pot is won by the player with the best *revealed* strength
      (bluffers can win with weak hands if unchallenged).

    Every player always receives a ``record_hand`` call so that all
    chip histories stay the same length regardless of bust status.
    """
    if len(players) < 2:
        return

    big_blind = max(1, big_blind)
    num_players = len(players)
    pot = 0
    active: list[tuple[HoldEmAgent, float, int]] = []  # (agent, raw_strength, position_index)

    # Track which players posted a blind so we can charge them on a fold
    posted_blind: set[str] = set()

    # Deal hands and post blinds
    for i, player in enumerate(players):
        if player.chips <= 0:
            continue  # busted players sit out but still get a zero record_hand below
        raw = rng.random()
        position_bonus = (i / max(1, num_players - 1)) * 0.15  # later = better position
        # Use min() so chips never go below zero during blind posting
        blind = min(big_blind, player.chips)
        player.chips -= blind
        player.total_invested += blind
        pot += blind
        posted_blind.add(player.name)

        if player.wants_to_enter_pot(raw, position_bonus):
            active.append((player, raw, i))

    # Net gains tracked per player; default 0 (busted / sitting-out players).
    # IMPORTANT: blind and call/raise amounts are already subtracted from
    # player.chips in-place above.  record_hand(net) will ADD net to the
    # current chip count, so:
    #   - winner receives the full pot (chips recover all prior deductions)
    #   - losers receive 0 (chips are already at the correct reduced value)
    net: dict[str, int] = {p.name: 0 for p in players}

    if not active:
        # Everyone folded pre-flop (degenerate) – return blinds
        for player in players:
            if player.name in posted_blind:
                player.chips += big_blind
                player.total_invested -= big_blind
                pot -= big_blind
        for player in players:
            player.record_hand(net[player.name])
        return

    # Post-flop betting round
    to_call = 0
    current_active = list(active)
    for player, raw, pos_idx in current_active:
        position_bonus = (pos_idx / max(1, num_players - 1)) * 0.15
        action, amount = player.decide_action(raw, pot, to_call, position_bonus)

        if action == "fold":
            active.remove((player, raw, pos_idx))
        elif action == "call":
            call_amount = min(amount, player.chips)
            player.chips -= call_amount
            player.total_invested += call_amount
            pot += call_amount
        elif action == "raise":
            raise_amount = min(amount, player.chips)
            player.chips -= raise_amount
            player.total_invested += raise_amount
            pot += raise_amount
            to_call = raise_amount
        # "check" – no money changes hands

    if not active:
        # All folded post-flop; pot is essentially lost (simplified model)
        for player in players:
            player.record_hand(0)
        return

    # Showdown – determine winner
    # Bluffers get a strength bonus proportional to their bluff_rate
    def showdown_strength(item: tuple[HoldEmAgent, float, int]) -> float:
        player, raw, _ = item
        bluff_bonus = rng.random() * player.bluff_rate * 0.25
        return raw + bluff_bonus

    active.sort(key=showdown_strength, reverse=True)
    winner, *_losers_info = active
    winner_agent = winner[0]

    # Winner receives the full pot; chips already had blind + bets deducted
    # in-place, so net_gain = pot gives the correct final chip count.
    # All other players record 0 – their chips are already at the final value.
    net[winner_agent.name] = pot

    # Record outcome for every player (busted players record 0)
    for player in players:
        player.record_hand(net[player.name])


def simulate_tournament(
    bots: Sequence[HoldEmAgent],
    num_hands: int = 500,
    seed: int = 42,
    big_blind: int = 10,
) -> dict[str, list[int]]:
    """Run a multi-hand tournament and return chip histories.

    Parameters
    ----------
    bots:
        Sequence of :class:`HoldEmAgent` instances.  Their state is reset
        before the simulation begins so the function is repeatable.
    num_hands:
        Number of hands to deal.
    seed:
        Master RNG seed for the deal (agent seeds are independent).
    big_blind:
        Starting big-blind size.

    Returns
    -------
    dict mapping agent name → list of chip counts (length = num_hands + 1).
    """
    # Reset agent state
    for bot in bots:
        bot.chips = 1000
        bot.hands_played = 0
        bot.hands_won = 0
        bot.total_invested = 0
        bot._rng = random.Random(bot.seed)
        bot.chip_history = [bot.chips]

    rng = random.Random(seed)

    for _ in range(num_hands):
        simulate_hand(bots, rng, big_blind=big_blind)

    return {bot.name: list(bot.chip_history) for bot in bots}


# ---------------------------------------------------------------------------
# Optional plotting
# ---------------------------------------------------------------------------


def plot_results(
    histories: dict[str, list[int]],
    title: str = "Texas Hold'em Bot Chip Histories",
    save_path: str | None = None,
) -> None:  # pragma: no cover
    """Plot chip-over-time curves for each bot.

    Requires ``matplotlib``.  If *save_path* is given the figure is saved
    to disk instead of (or in addition to) being displayed.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("matplotlib is required for plotting: pip install matplotlib") from exc

    fig, ax = plt.subplots(figsize=(12, 6))
    for name, history in histories.items():
        ax.plot(history, label=name)

    ax.set_title(title)
    ax.set_xlabel("Hands Played")
    ax.set_ylabel("Chips")
    ax.legend(loc="upper left")
    ax.axhline(y=1000, color="gray", linestyle="--", linewidth=0.8, label="Starting chips")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
    plt.show()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    """Run a demonstration tournament and (optionally) plot results."""
    import argparse

    parser = argparse.ArgumentParser(description="Simulate Texas Hold'em bots")
    parser.add_argument("--hands", type=int, default=500, help="Number of hands to deal")
    parser.add_argument("--seed", type=int, default=42, help="Master RNG seed")
    parser.add_argument("--plot", action="store_true", help="Plot chip histories (requires matplotlib)")
    parser.add_argument("--save", type=str, default=None, help="Save plot to file")
    args = parser.parse_args()

    print(f"Simulating {args.hands} hands with {len(BOTS)} bots (seed={args.seed})…\n")

    histories = simulate_tournament(BOTS, num_hands=args.hands, seed=args.seed)

    for bot in BOTS:
        print(
            f"  {bot.name:<10}  chips={bot.chips:>6}  "
            f"hands={bot.hands_played:>4}  won={bot.hands_won:>4}  "
            f"win%={bot.win_rate * 100:5.1f}%"
        )

    if args.plot or args.save:
        plot_results(histories, save_path=args.save)


if __name__ == "__main__":
    main()

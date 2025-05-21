#GameState.py
class GameState:
    def __init__(self, player_count=8, wolf_count=2, seer_count=1, hunter_count=0, witch_count=0):
        self.player_count = player_count
        self.wolf_count = wolf_count
        self.initial_wolf_count = wolf_count  # 记录初始狼人数量
        self.seer_count = seer_count
        self.initial_seer_count = seer_count  # 记录初始预言家数量
        self.hunter_count = hunter_count
        self.initial_hunter_count = hunter_count  # 记录初始猎人数量
        self.witch_count = witch_count
        self.initial_witch_count = witch_count  # 记录初始女巫数量
        self.players = {}
        self.day = 0  # 从第0天开始，第0天是警长选举阶段
        self.dead_today = []
        self.dead_yesterday = []
        self.day_votes = {}
        self.night_votes = {}
        self.phase = "day"
        self.history = []
        self.current_day_summary = {"deaths": []}  # 记录 (player_id, death_cause)
        
        # 女巫能力相关状态
        self.wolf_kill_target = None  # 记录当晚狼人击杀的目标，用于女巫救人判断
        self.witch_save_used = {}  # 记录每个女巫是否已使用救人药，格式{player_id: True/False}
        self.witch_poison_used = {}  # 记录每个女巫是否已使用毒药，格式{player_id: True/False}
        self.witch_save_target = None  # 记录被女巫救活的目标
        
        # 警长相关状态
        self.sheriff_id = None  # 当前警长玩家ID
        self.sheriff_history = []  # 历史警长记录，格式为[(player_id, "当选"/"移交"/"销毁"), ...]
        
        self.initialize_players()

    def initialize_players(self):
        for i in range(1, self.player_count + 1):
            self.players[i] = Player(i, f"玩家 {i}")
        
        # 初始化女巫药水状态
        self.witch_save_used = {}
        self.witch_poison_used = {}
        
    def reset_day(self):
        summary = {
            "day": self.day,
            "deaths": self.current_day_summary.get("deaths", [])
        }
        self.history.append(summary)
        self.dead_yesterday = self.dead_today.copy()
        self.dead_today = []
        self.day_votes = {}
        self.night_votes = {}
        self.current_day_summary = {"deaths": []}
        self.wolf_kill_target = None  # 重置狼人击杀目标
        self.witch_save_target = None  # 重置女巫救人目标
        self.day += 1

    def check_game_over(self):
        alive_wolves = sum(1 for p in self.players.values() if p.exists and p.alive and p.identity == "狼人")
        alive_civilians = sum(1 for p in self.players.values() if p.exists and p.alive and p.identity != "狼人")
        if alive_wolves == 0:
            return True, "平民阵营"
        if alive_civilians == 0:
            return True, "狼人阵营"
        if alive_wolves >= alive_civilians and alive_civilians > 0:
            return True, "狼人阵营"
        return False, None

class Player:
    def __init__(self, player_id, name, identity="平民", model="gemini"):
        self.player_id = player_id
        self.name = name
        self.identity = identity
        self.model = model
        self.alive = True
        self.exists = True
        self.vote_history = []
        self.death_reason = None  # 添加死亡原因属性
        self.death_day = None     # 添加死亡日期属性

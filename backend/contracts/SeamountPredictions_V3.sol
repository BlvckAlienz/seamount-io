// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SeamountPredictions V2.4 - ZERO LOOPS VERSION
 * @notice Removed all loops, absolute minimal stack usage
 */

contract SeamountPredictions {
    
    uint256 private _guard = 1;
    address private _owner;
    bool private _paused;
    
    modifier nonReentrant() {
        require(_guard == 1);
        _guard = 2;
        _;
        _guard = 1;
    }
    
    modifier onlyOwner() {
        require(msg.sender == _owner);
        _;
    }
    
    modifier whenNotPaused() {
        require(!_paused);
        _;
    }
    
    uint256 public constant LOW_FEE = 10;
    uint256 public constant MED_FEE = 7;
    uint256 public constant HIGH_FEE = 5;
    uint256 public constant DEADLINE = 90 days;
    uint256 public constant MULTIPLIER = 10000;
    uint256 public constant MIN_BET = 0.01 ether;
    uint256 public constant MIN_BOOT = 1 ether;
    uint256 public constant MAX_ODDS = 9500;
    uint256 public constant MIN_ODDS = 500;
    
    address public feeCollector;
    uint256 public marketCount;
    uint256 public totalFees;
    
    struct Market {
        string question;
        uint256 endTime;
        uint256 resolutionTime;
        bool resolved;
        bool outcome;
        bool bootstrapped;
        uint256 lockedYes;
        uint256 lockedNo;
        uint256 lockedTotal;
        uint256 currentYes;
        uint256 currentNo;
        uint256 participants;
    }
    
    mapping(uint256 => Market) public markets;
    mapping(uint256 => mapping(address => uint256)) public yesBets;
    mapping(uint256 => mapping(address => uint256)) public noBets;
    mapping(uint256 => mapping(address => bool)) public claimed;
    mapping(uint256 => mapping(address => bool)) public participated;
    
    event Created(uint256 indexed id, string question, uint256 endTime);
    event Bootstrapped(uint256 indexed id, uint256 yes, uint256 no);
    event BetPlaced(uint256 indexed id, address indexed user, bool prediction, uint256 amount);
    event Resolved(uint256 indexed id, bool outcome);
    event Claimed(uint256 indexed id, address indexed user, uint256 amount);
    
    constructor() {
        _owner = msg.sender;
        feeCollector = msg.sender;
    }
    
    function createMarket(string memory question, uint256 endTime) external onlyOwner whenNotPaused returns (uint256) {
        require(endTime > block.timestamp);
        require(bytes(question).length > 0 && bytes(question).length <= 500);
        
        uint256 id = marketCount++;
        Market storage m = markets[id];
        m.question = question;
        m.endTime = endTime;
        
        emit Created(id, question, endTime);
        return id;
    }
    
    function bootstrapMarket(uint256 id) external payable onlyOwner {
        require(id < marketCount);
        require(msg.value >= MIN_BOOT);
        
        Market storage m = markets[id];
        require(!m.bootstrapped);
        require(block.timestamp < m.endTime);
        
        uint256 half = msg.value / 2;
        m.currentYes = half;
        m.currentNo = msg.value - half;
        m.bootstrapped = true;
        
        emit Bootstrapped(id, m.currentYes, m.currentNo);
    }
    
    function bet(uint256 id, bool prediction) external payable nonReentrant whenNotPaused {
        require(id < marketCount);
        require(msg.value >= MIN_BET);
        
        Market storage m = markets[id];
        require(block.timestamp < m.endTime);
        require(!m.resolved);
        require(m.bootstrapped);
        
        if (!participated[id][msg.sender]) {
            participated[id][msg.sender] = true;
            m.participants++;
        }
        
        if (prediction) {
            yesBets[id][msg.sender] += msg.value;
            m.currentYes += msg.value;
        } else {
            noBets[id][msg.sender] += msg.value;
            m.currentNo += msg.value;
        }
        
        emit BetPlaced(id, msg.sender, prediction, msg.value);
    }
    
    function resolve(uint256 id, bool outcome) external onlyOwner {
        require(id < marketCount);
        
        Market storage m = markets[id];
        require(!m.resolved);
        require(block.timestamp >= m.endTime);
        
        m.lockedYes = m.currentYes;
        m.lockedNo = m.currentNo;
        m.lockedTotal = m.currentYes + m.currentNo;
        m.resolved = true;
        m.outcome = outcome;
        m.resolutionTime = block.timestamp;
        
        emit Resolved(id, outcome);
    }
    
    function claim(uint256 id) external nonReentrant {
        require(id < marketCount);
        
        Market storage m = markets[id];
        require(m.resolved);
        require(!claimed[id][msg.sender]);
        require(block.timestamp < m.resolutionTime + DEADLINE);
        
        uint256 userBet = m.outcome ? yesBets[id][msg.sender] : noBets[id][msg.sender];
        require(userBet > 0);
        
        uint256 pool = m.outcome ? m.lockedYes : m.lockedNo;
        require(pool > 0);
        
        uint256 gross = (userBet * m.lockedTotal) / pool;
        uint256 feeRate = m.lockedTotal < 1000 ether ? LOW_FEE : m.lockedTotal < 10000 ether ? MED_FEE : HIGH_FEE;
        uint256 fee = (gross * feeRate) / 1000;
        uint256 net = gross - fee;
        
        claimed[id][msg.sender] = true;
        totalFees += fee;
        
        payable(msg.sender).transfer(net);
        payable(feeCollector).transfer(fee);
        
        emit Claimed(id, msg.sender, net);
    }
    
    function recover(uint256 id) external onlyOwner {
        require(id < marketCount);
        Market storage m = markets[id];
        require(m.resolved);
        require(block.timestamp >= m.resolutionTime + DEADLINE);
        
        uint256 bal = address(this).balance;
        if (bal > 0) payable(feeCollector).transfer(bal);
    }
    
    function odds(uint256 id) external view returns (uint256 yes, uint256 no) {
        require(id < marketCount);
        Market storage m = markets[id];
        
        uint256 y = m.currentYes;
        uint256 n = m.currentNo;
        
        if (y == 0 && n == 0) return (5000, 5000);
        if (y == 0) return (MIN_ODDS, MAX_ODDS);
        if (n == 0) return (MAX_ODDS, MIN_ODDS);
        
        uint256 total = y + n;
        yes = (y * MULTIPLIER) / total;
        if (yes > MAX_ODDS) yes = MAX_ODDS;
        if (yes < MIN_ODDS) yes = MIN_ODDS;
        no = MULTIPLIER - yes;
    }
    
    function getMarket(uint256 id) external view returns (string memory, uint256, bool, bool) {
        require(id < marketCount);
        Market storage m = markets[id];
        return (m.question, m.endTime, m.resolved, m.outcome);
    }
    
    function getPools(uint256 id) external view returns (uint256, uint256, uint256) {
        require(id < marketCount);
        Market storage m = markets[id];
        return (m.currentYes, m.currentNo, m.participants);
    }
    
    function getUserBet(uint256 id, address user) external view returns (uint256, uint256, bool) {
        require(id < marketCount);
        return (yesBets[id][user], noBets[id][user], claimed[id][user]);
    }
    
    function pause() external onlyOwner { _paused = true; }
    function unpause() external onlyOwner { _paused = false; }
    
    function setFeeCollector(address a) external onlyOwner {
        require(a != address(0));
        feeCollector = a;
    }
    
    function emergencyWithdraw() external onlyOwner {
        require(_paused);
        payable(_owner).transfer(address(this).balance);
    }
}
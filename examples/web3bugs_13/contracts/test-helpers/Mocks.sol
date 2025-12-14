
// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

import "../interfaces/IRCTreasury.sol";
import "../interfaces/IRCNftHubL2.sol";
import "../interfaces/IRCOrderbook.sol";
import "../interfaces/IRealitio.sol";
import "../RCMarket.sol";

contract ArgusMockTreasury is IRCTreasury {
    mapping(address => uint256) public userDeposits;
    mapping(address => bool) public foreclosedStatus;

    receive() external payable {}
    fallback() external payable {}

    function deposit() external payable {
        userDeposits[msg.sender] += msg.value;
    }

    function setForeclosed(address user, bool status) external {
        foreclosedStatus[user] = status;
    }

    function isForeclosed(address user) external view override returns (bool) {
        return foreclosedStatus[user];
    }

    function collectRentUser(address, uint256) external override returns (uint256) {
        return 0;
    }
    
    function payout(address recipient, uint256 amount) external override returns (bool) {
        (bool success, ) = payable(recipient).call{value: amount}("");
        require(success, "Transfer failed");
        return true;
    }

    function refundUser(address user, uint256 amount) external override {
        userDeposits[user] += amount;
    }

    function payRent(uint256) external override returns (bool) { return true; }
    function updateLastRentalTime(address) external override returns (bool) { return true; }
    function userDeposit(address user) external view override returns (uint256) { return userDeposits[user]; }
    function userTotalBids(address) external view override returns (uint256) { return 0; }
    function minRentalDayDivisor() external view override returns (uint256) { return 24; }
    function marketPaused(address) external view override returns (bool) { return false; }
    function globalPause() external view override returns (bool) { return false; }
    function sponsor(address, uint256) external override returns (bool) { return true; }
    function checkSponsorship(address, uint256) external view override {}
    
    function addMarket(address) external override {}
    function addToWhitelist(address) external override {}
    function batchAddToWhitelist(address[] calldata) external override {}
    function bridgeAddress() external view override returns (address) { return address(0); }
    function changeGlobalPause() external override {}
    function changePauseMarket(address) external override {}
    function changeUberOwner(address) external override {}
    function decreaseBidRate(address, uint256) external override {}
    function deposit(uint256, address) external override returns (bool) { return true; }
    function erc20() external override returns (IERC20) { return IERC20(address(0)); }
    function factoryAddress() external view override returns (address) { return address(0); }
    function foreclosureTimeUser(address) external view override returns (uint256, uint256) { return (0,0); }
    function increaseBidRate(address, uint256) external override {}
    function isMarket(address) external view override returns (bool) { return true; }
    function marketPot(address) external view override returns (uint256) { return 0; }
    function maxContractBalance() external view override returns (uint256) { return 1e30; }
    function resetUser(address) external override {}
    function setBridgeAddress(address) external override {}
    function setFactoryAddress(address) external override {}
    function setMaxContractBalance(uint256) external override {}
    function setMinRental(uint256) external override {}
    function setTokenAddress(address) external override {}
    function toggleWhitelist() external override {}
    function topupMarketBalance(uint256) external override {}
    function totalDeposits() external view override returns (uint256) { return 0; }
    function totalMarketPots() external view override returns (uint256) { return 0; }
    function uberOwner() external view override returns (address) { return address(0); }
    function updateRentalRate(address, uint256, bool) external override {}
    function withdrawDeposit(uint256, bool) external override {}
}

contract ArgusMockNftHub is IRCNftHubL2 {
    mapping(uint256 => address) public owners;

    function ownerOf(uint256 tokenId) public view override returns (address) {
        return owners[tokenId];
    }

    function transferNft(address from, address to, uint256 tokenId) external override returns (bool) {
        require(owners[tokenId] == from, "Not owner");
        owners[tokenId] = to;
        return true;
    }

    function mint(address to, uint256 tokenId) external {
        owners[tokenId] = to;
    }

    function withdrawWithMetadata(uint256) external override {}
    function tokenURI(uint256) external pure override returns (string memory) { return ""; }

    function addMarket(address) external override {}
    function deposit(address, bytes calldata) external override {}
    function marketTracker(uint256) external view override returns (address) { return address(0); }
    function mint(uint256, address, string calldata) external override {}
    function withdraw(uint256) external override {}
}

contract ArgusMockOrderbook is IRCOrderbook {
    event UserRemoved(address indexed user);

    function addBidToOrderbook(address, uint256, uint256, uint256, address) external override {}
    function removeOldBids(address) external override {}
    function getBidValue(address, uint256) external pure override returns (uint256) { return 0; }
    function setTimeHeldlimit(address, uint256, uint256) external override {}
    function findNewOwner(uint256, uint256) external override returns (address, uint256, uint256) { return (address(0), 0, 0); }
    function bidExists(address, address, uint256) external pure override returns (bool) { return false; }
    function removeBidFromOrderbook(address, uint256) external override {}
    function reduceTimeHeldLimit(address, uint256, uint256) external override {}
    function closeMarket() external override {}
    
    function removeUserFromOrderbook(address user) external override returns (bool) {
        emit UserRemoved(user);
        return true;
    }

    function addMarket(address, uint256, uint256) external override {}
    function changeUberOwner(address) external override {}
    function getTimeHeldlimit(address, uint256) external view override returns (uint256) { return 0; }
    function setFactoryAddress(address) external override {}
    function setLimits(uint256, uint256) external override {}
}

contract ArgusMockRealitio is IRealitio {
    mapping(bytes32 => bytes32) results;
    mapping(bytes32 => bool) finalized;

    function askQuestion(uint16, string calldata, address, uint32, uint32, uint8) external override returns (bytes32) {
        bytes32 questionId = keccak256(abi.encodePacked(block.timestamp, msg.sender));
        return questionId;
    }

    function isFinalized(bytes32 questionId) external view override returns (bool) {
        return finalized[questionId];
    }

    function resultFor(bytes32 questionId) external view override returns (bytes32) {
        return results[questionId];
    }

    function setResultFor(bytes32 questionId, bytes32 result) external {
        results[questionId] = result;
        finalized[questionId] = true;
    }

    function askQuestion(uint256, string calldata, address, uint32, uint256) external override returns (bytes32) { return bytes32(0); }
    function getContentHash(bytes32) external view override returns (bytes32) { return bytes32(0); }
}

contract ArgusReentrancyAttacker is IRCOrderbook {
    RCMarket public market;
    uint256 public callCount = 0;

    constructor(address _market) {
        market = RCMarket(_market);
    }

    function closeMarket() external override {
        callCount++;
        if (callCount < 2) {
            market.lockMarket();
        }
    }
    
    function addBidToOrderbook(address, uint256, uint256, uint256, address) external override {}
    function removeOldBids(address) external override {}
    function getBidValue(address, uint256) external pure override returns (uint256) { return 0; }
    function setTimeHeldlimit(address, uint256, uint256) external override {}
    function findNewOwner(uint256, uint256) external override returns (address, uint256, uint256) { return (address(0), 0, 0); }
    function bidExists(address, address, uint256) external pure override returns (bool) { return false; }
    function removeBidFromOrderbook(address, uint256) external override {}
    function reduceTimeHeldLimit(address, uint256, uint256) external override {}
    function removeUserFromOrderbook(address) external override returns (bool) { return true; }
    function addMarket(address, uint256, uint256) external override {}
    function changeUberOwner(address) external override {}
    function getTimeHeldlimit(address, uint256) external view override returns (uint256) { return 0; }
    function setFactoryAddress(address) external override {}
    function setLimits(uint256, uint256) external override {}
}

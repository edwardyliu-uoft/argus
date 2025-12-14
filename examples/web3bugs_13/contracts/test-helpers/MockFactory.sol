
// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

import "../RCMarket.sol";
import "../interfaces/IRCTreasury.sol";
import "../interfaces/IRCNftHubL2.sol";
import "../interfaces/IRCOrderbook.sol";
import "../interfaces/IRealitio.sol";

contract ArgusMockFactory {
    address public owner;
    IRCTreasury public treasury;
    IRCNftHubL2 public nfthub;
    IRCOrderbook public orderbook;
    IRealitio public realitio;
    address public arbitrator;
    uint32 public timeout;

    event LogNewMarket(address indexed market, address indexed creator);

    constructor() {
        owner = msg.sender;
    }

    function createMarket(
        uint256 _mode,
        uint32[] memory _timestamps,
        uint256 _numberOfCards,
        uint256 _totalNftMintCount,
        address _artistAddress,
        address _affiliateAddress,
        address[] memory _cardAffiliateAddresses,
        address _marketCreatorAddress,
        string calldata _realitioQuestion
    ) external returns (address) {
        RCMarket market = new RCMarket();
        market.initialize(
            _mode,
            _timestamps,
            _numberOfCards,
            _totalNftMintCount,
            _artistAddress,
            _affiliateAddress,
            _cardAffiliateAddresses,
            _marketCreatorAddress,
            _realitioQuestion
        );
        emit LogNewMarket(address(market), _marketCreatorAddress);
        return address(market);
    }

    function setOwner(address _owner) external {
        owner = _owner;
    }

    function setTreasury(address _treasury) external {
        treasury = IRCTreasury(_treasury);
    }

    function setNftHub(address _nfthub) external {
        nfthub = IRCNftHubL2(_nfthub);
    }

    function setOrderbook(address _orderbook) external {
        orderbook = IRCOrderbook(_orderbook);
    }

    function setOracleSettings(address _realitio, address _arbitrator, uint32 _timeout) external {
        realitio = IRealitio(_realitio);
        arbitrator = _arbitrator;
        timeout = _timeout;
    }
    
    function getOracleSettings() external view returns (IRealitio, address, uint32) {
        return (realitio, arbitrator, timeout);
    }

    function getPotDistribution() external pure returns (uint256[5] memory) {
        // artistCut, winnerCut, creatorCut, affiliateCut, cardAffiliateCut
        uint256[5] memory cuts = [100, 100, 50, 0, 0];
        return cuts;
    }

    function minimumPriceIncreasePercent() external pure returns (uint256) {
        return 10;
    }

    function maxRentIterations() external pure returns (uint256) {
        return 10;
    }

    function isMarketApproved(address) external pure returns (bool) {
        return true;
    }

    function trapIfUnapproved() external pure returns (bool) {
        return false;
    }
}

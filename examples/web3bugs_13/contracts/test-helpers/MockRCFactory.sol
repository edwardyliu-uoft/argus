// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

import "../RCMarket.sol";
import "../interfaces/IRCTreasury.sol";
import "../interfaces/IRCNftHubL2.sol";
import "../interfaces/IRCOrderbook.sol";
import "../interfaces/IRealitio.sol";

contract MockRCFactory {
    IRCTreasury public treasury;
    IRCNftHubL2 public nfthub;
    IRCOrderbook public orderbook;
    IRealitio public realitio;
    address public owner;

    event LogNewMarket(address indexed market, address indexed creator);

    constructor(address _treasury, address _nfthub, address _orderbook, address _realitio) {
        treasury = IRCTreasury(_treasury);
        nfthub = IRCNftHubL2(_nfthub);
        orderbook = IRCOrderbook(_orderbook);
        realitio = IRealitio(_realitio);
        owner = msg.sender;
    }

    function createMarket(
        uint256 _mode,
        uint32[] memory _timestamps,
        uint256 _numberOfCards,
        address _artistAddress,
        address _affiliateAddress,
        address[] memory _cardAffiliateAddresses,
        address _marketCreatorAddress,
        string calldata _realitioQuestion
    ) external {
        RCMarket market = new RCMarket();
        market.initialize(
            _mode,
            _timestamps,
            _numberOfCards,
            0, // totalNftMintCount
            _artistAddress,
            _affiliateAddress,
            _cardAffiliateAddresses,
            _marketCreatorAddress,
            _realitioQuestion
        );
        // Mint NFTs to the market
        for (uint i = 0; i < _numberOfCards; i++) {
            nfthub.transferNft(address(0), address(market), i);
        }
        emit LogNewMarket(address(market), msg.sender);
    }

    function getPotDistribution() external pure returns (uint256[5] memory) {
        // [artist, winner, creator, affiliate, cardAffiliate]
        uint256[5] memory dist = [uint256(100), 600, 100, 100, 100];
        return dist;
    }

    function minimumPriceIncreasePercent() external pure returns (uint256) { return 10; }
    function maxRentIterations() external pure returns (uint256) { return 20; }

    function getOracleSettings() external view returns (IRealitio, address, uint32) {
        return (realitio, address(0), 3600);
    }

    function isMarketApproved(address) external view returns (bool) { return true; }
    function trapIfUnapproved() external view returns (bool) { return false; }

    function setTreasury(address _newTreasury) external {
        treasury = IRCTreasury(_newTreasury);
    }
}

// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../../contracts/interfaces/IRCNftHubL2.sol";

contract MockRCNftHubL2 is IRCNftHubL2 {
    function addMarket(address) external override {}
    function mint(address, uint256, string memory) external override returns (bool) {
        return true;
    }
    function airdrop(address, uint256) external override {}
    function isApprovedOrOwner(address, uint256) external view override returns (bool) { return true; }
    function transferFrom(address, address, uint256) external override {}
    function safeTransferFrom(address, address, uint256) external override {}
    function safeTransferFrom(address, address, uint256, bytes memory) external override {}
    function setApprovalForAll(address, bool) external override {}
    function marketTracker(uint256) external view override returns (address) { return address(0); }
    function ownerOf(uint256) external view override returns (address) { return address(0); }
    function tokenURI(uint256) external view override returns (string memory) { return ""; }
    function transferNft(address, address, uint256, bool) external override {}
    function deposit(address, bytes calldata) external override {}
    function withdraw(uint256) external override {}
    function withdrawWithMetadata(uint256) external override {}
}

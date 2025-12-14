// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../../contracts/interfaces/IRCTreasury.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract MockRCTreasury is IRCTreasury {
    bool private _checkSponsorship;

    function checkSponsorship(address, uint256) external view override {
        require(_checkSponsorship, "Sponsorship check failed");
    }

    function setCheckSponsorship(bool shouldPass) external {
        _checkSponsorship = shouldPass;
    }

    function addMarket(address) external override {}
    function isForeclosed(address) external view override returns (bool) { return false; }
    function collectRentUser(address, uint256) external override {}
    function deposit(uint256, address) external override returns (bool) { return true; }
    function withdrawDeposit(uint256, bool) external override {}
    function userBalance(address) external view override returns (uint256) { return 0; }
    function token() external view override returns (address) { return address(0); }
    function setTokenAddress(address) external override {}
    function foreclosureTimeUser(address) external view override returns (uint256) { return 0; }
    function refundUser(address, uint256) external override {}
    function bridgeAddress() external view override returns (address) { return address(0); }
    function factoryAddress() external view override returns (address) { return address(0); }
    function isMarket(address) external view returns (bool) { return true; }
    function totalDeposits() external view returns (uint256) { return 0; }
    function marketPot(address) external view returns (uint256) { return 0; }
    function totalMarketPots() external view returns (uint256) { return 0; }
    function minRentalDayDivisor() external view returns (uint256) { return 0; }
    function maxContractBalance() external view returns (uint256) { return 0; }
    function globalPause() external view returns (bool) { return false; }
    function marketPaused(address) external view returns (bool) { return false; }
    function uberOwner() external view returns (address) { return address(0); }
    function setMinRental(uint256) external override {}
    function setMaxContractBalance(uint256) external override {}
    function setBridgeAddress(address) external override {}
    function changeGlobalPause() external override {}
    function changePauseMarket(address) external override {}
    function setFactoryAddress(address) external override {}
    function changeUberOwner(address) external override {}
    function erc20() external override returns (IERC20) { return IERC20(address(0)); }
    function payRent(uint256) external override returns (bool) { return true; }
    function payout(address, uint256) external override returns (bool) { return true; }
    function sponsor(address, uint256) external override returns (bool) { return true; }
    function updateLastRentalTime(address) external override returns (bool) { return true; }
    function userTotalBids(address) external view override returns (uint256) { return 0; }
    function updateRentalRate(address, uint256, bool) external override {}
    function increaseBidRate(address, uint256) external override {}
    function decreaseBidRate(address, uint256) external override {}
    function resetUser(address) external override {}
    function userDeposit(address) external view override returns (uint256) { return 0; }
    function topupMarketBalance(uint256) external override {}
    function toggleWhitelist() external override {}
    function addToWhitelist(address) external override {}
    function batchAddToWhitelist(address[] calldata) external override {}
}

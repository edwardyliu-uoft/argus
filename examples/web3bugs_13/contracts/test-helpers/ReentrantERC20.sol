// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "./MockERC20.sol";
import "../interfaces/IRCTreasury.sol";

contract ReentrantERC20 is MockERC20 {
    IRCTreasury private _treasury;
    address private _attacker;
    uint256 private _reentrantAmount;
    bool private _reentrancyGuard = false;

    constructor(string memory name, string memory symbol) MockERC20(name, symbol) {}

    function setAttack(address treasury, address attacker, uint256 amount) public {
        _treasury = IRCTreasury(treasury);
        _attacker = attacker;
        _reentrantAmount = amount;
    }

    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        if (from == _attacker && to == address(_treasury) && !_reentrancyGuard) {
            _reentrancyGuard = true;
            // Re-enter the deposit function
            _treasury.deposit(_reentrantAmount, _attacker);
            _reentrancyGuard = false;
        }
        return super.transferFrom(from, to, amount);
    }
}

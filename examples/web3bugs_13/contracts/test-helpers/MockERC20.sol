// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockERC20 is ERC20 {
    bool private _transferSuccess = true;

    constructor(string memory name, string memory symbol) ERC20(name, symbol) {}

    function mint(address to, uint256 amount) public {
        _mint(to, amount);
    }

    function setTransferSuccess(bool success) public {
        _transferSuccess = success;
    }

    function transfer(address to, uint256 amount) public virtual override returns (bool) {
        if (!_transferSuccess) {
            return false;
        }
        return super.transfer(to, amount);
    }

    function transferFrom(address from, address to, uint256 amount) public virtual override returns (bool) {
        if (!_transferSuccess) {
            return false;
        }
        return super.transferFrom(from, to, amount);
    }
}

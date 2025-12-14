// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract MockRCNftHubL2 is ERC721 {
    mapping(uint256 => address) public owners;
    address public factory;

    constructor() ERC721("MockNftHub", "MNFT") {}

    function setFactory(address _factory) external {
        factory = _factory;
    }

    function transferNft(address _from, address _to, uint256 _tokenId) external returns (bool) {
        if (owners[_tokenId] == address(0) && _from == address(0)) {
            owners[_tokenId] = _to;
        } else {
            require(owners[_tokenId] == _from, "Not owner");
            owners[_tokenId] = _to;
        }
        return true;
    }

    function ownerOf(uint256 _tokenId) public view override returns (address) {
        if (owners[_tokenId] == address(0)) {
            return address(this); // Default owner if not set
        }
        return owners[_tokenId];
    }

    function withdrawWithMetadata(uint256) external {}

    function tokenURI(uint256) public view override returns (string memory) {
        return "";
    }
}

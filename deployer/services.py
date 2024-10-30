from django.conf import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from django.core.cache import cache
import hashlib


class CounterDeploymentService:
    def __init__(self):
        self.base_dir = settings.BASE_DIR
        self.src_dir = None
        self.out_path = None
        self.contract_path = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.cache_dir = settings.BASE_DIR / 'contract_cache'
        self.cache_dir.mkdir(exist_ok=True)
        self.contract_content = ('// SPDX-License-Identifier: MIT\n'
            'pragma solidity ^0.8.24;\n\n'
            'contract Counter {\n'
            '\tuint256 public number;\n'
            '\tfunction setNumber(uint256 newNumber) public {\n'
            '\t\tnumber = newNumber;\n'
            '\t}\n\n'
            '\tfunction increment() public {\n'
            '\t\tnumber++;\n'
            '\t}\n'
            '}')
        
    def _get_cache_key(self):
        return f'counter_contract_{hashlib.md5(self.contract_content.encode()).hexdigest()}'
    
    def _get_cached_contract_data(self):
        """Retrieve cached contract data"""
        cache_key = self._get_cache_key()
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        return None
    
    def _save_contract_data(self, contract_data):
        """Cache new data"""
        cache_key = self._get_cache_key()
        cache.set(cache_key, contract_data, timeout=720000)
        
        
    async def _async_subprocess(self, cmd, cwd=None, timeout=300):
        """Run subprocess command asynchronously with timeout"""
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                if process.returncode != 0:
                    error_msg = stderr.decode()
                    raise Exception(f'Command failed: {error_msg}')
                return stdout.decode()
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f'Command timed out after {timeout} seconds')
        except Exception as e:
            raise Exception(f'Subprocess error: {e}')
        
    def _setup_project(self):
        """Create toml file and src directory"""
        try:
            foundry_toml_path = self.base_dir / 'foundry.toml'
            if foundry_toml_path.exists():
                return
            with open(foundry_toml_path, 'w') as file:
                file.write(
                    '[profile.default]\n' +
                    "src = 'src'\n" +
                    "libs = ['lib']\n" +
                    'fallback_oz = true\n' +
                    'is_system = false\n' +
                    'mode = "3"'
                )
                
            self.src_dir = self.base_dir / 'src'
            self.src_dir.mkdir(exist_ok=True)
        except Exception as e:
            raise Exception(f'Project setup failed: {e}')
    
    def _create_contract_file(self):
        """Create counter contract file"""
        try:
            self.contract_path = self.src_dir / 'Counter.sol'
            with open(self.contract_path, 'w') as file:
                file.write(self.contract_content)
        except Exception as e:
            raise Exception(f'Contract file creation failed: {e}')
        
    async def _compile_contract(self):
        """Compile counter contract"""
        try:
            await self._async_subprocess(
                ['forge', 'clean'],
                cwd=self.base_dir,
                timeout=60
            )
            
            await self._async_subprocess(
                ['forge', 'init', '--force', '--no-git', '--no-commit', '.'],
                cwd=self.base_dir,
                timeout=60
            )
            
            self.out_path = self.base_dir / 'zkout' / 'Counter.sol' / 'Counter.json'
            if not self.out_path.exists():
                await self._async_subprocess(
                    ['forge', 'build', '--zksync'],
                    cwd=self.base_dir,
                    timeout=300
                )
        except Exception as e:
            raise Exception(f'Contract compilation failed: {e}')
        
    def _get_contract_data(self):
        try:
            with open(self.out_path) as file:
                data = json.load(file)
            
            contract_data_value = (
                '0x9c4d535b0000000000000000000000000000000000000000000000000000000000000000'  # is_system flag
                f'{data["hash"]}'  # factory dependency hash from compiler
                '00000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000000'  # calldata length
            )
            return {'contract_data_value': contract_data_value}
        except Exception as e:
            raise Exception(f'Contract data error: {e}')
        
    async def prepare_deployment(self):
        """Initiate new deployment process or use cached data"""
        try:
            cached_data = self._get_cached_contract_data()
            if cached_data:
                return {
                    'success': True,
                    'contract_data': cached_data
                }
                
            self._setup_project()
            self._create_contract_file()
            await self._compile_contract()
            contract_data = self._get_contract_data()
            
            # Cache new contract data
            self._save_contract_data(contract_data)
            return {
                'success': True,
                'contract_data': contract_data
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Deployment failed: {e}'
            }
        
    async def verify_contract(self, contract_address):
        try:
            await self._async_subprocess(
                ['forge', 'verify-contract', f'{contract_address}', 'src/Counter.sol:Counter',
                '--verifier', 'zksync', '--verifier-url',
                'https://api-explorer-verify.testnet.abs.xyz/contract_verification',
                '--zksync'],
                cwd=self.base_dir,
                timeout=300
                )

            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': f'Deployment failed: {e}'
            }
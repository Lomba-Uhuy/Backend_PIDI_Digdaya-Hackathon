import { Controller, Get, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { MarketService } from './market.service.js';

@ApiTags('Market Reference')
@Controller('market')
export class MarketController {
  constructor(private readonly marketService: MarketService) {}

  @Get('hs-codes')
  @ApiOperation({ summary: 'HS codes that have real ingested trade data' })
  hsCodes() {
    return this.marketService.hsCodes();
  }

  @Get('top-markets')
  @ApiOperation({ summary: 'Top destination countries for an HS chapter (real BPS data)' })
  topMarkets(@Query('hs') hs?: string, @Query('flow') flow?: string) {
    return this.marketService.topMarkets(hs ?? '09', flow === 'M' ? 'M' : 'X');
  }

  @Get('regions')
  @ApiOperation({ summary: 'Destination countries present in the trade data' })
  regions() {
    return this.marketService.regions();
  }
}

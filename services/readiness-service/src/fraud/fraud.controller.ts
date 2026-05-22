import { Body, Controller, Post } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { IsOptional, IsString, IsUUID, MaxLength, MinLength } from 'class-validator';
import { FraudDetectionService } from './fraud-detection.service.js';

class FraudScanDto {
  @IsUUID()
  buyerId!: string;

  @IsString() @MinLength(1) @MaxLength(20_000)
  termsText!: string;

  @IsString() @MaxLength(50_000) @IsOptional()
  contractText?: string;
}

@ApiTags('Fraud Detection')
@Controller('fraud')
export class FraudController {
  constructor(private readonly fraud: FraudDetectionService) {}

  @Post('scan')
  scan(@Body() dto: FraudScanDto) {
    return this.fraud.scan(dto.buyerId, dto.termsText, dto.contractText);
  }
}
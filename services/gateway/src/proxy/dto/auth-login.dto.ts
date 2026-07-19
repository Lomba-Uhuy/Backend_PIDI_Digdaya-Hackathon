import { ApiProperty } from '@nestjs/swagger';
import { IsEmail, IsString, MinLength } from 'class-validator';

export class AuthLoginDto {
  @ApiProperty({ example: 'owner@kopigayo.id', format: 'email' })
  @IsEmail()
  email!: string;

  @ApiProperty({ example: 'KopiGayo!2026', minLength: 8 })
  @IsString()
  @MinLength(8)
  password!: string;
}

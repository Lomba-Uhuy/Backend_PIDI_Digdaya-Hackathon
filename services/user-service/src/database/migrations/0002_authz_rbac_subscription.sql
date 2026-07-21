-- RBAC role on users + per-user subscription (plan/status/usage/feature flags).
-- Idempotent so it is safe on databases where objects may already exist.
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "role" varchar(32) NOT NULL DEFAULT 'umkm';--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "subscription" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"plan" varchar(32) DEFAULT 'free' NOT NULL,
	"status" varchar(24) DEFAULT 'active' NOT NULL,
	"billing_cycle" varchar(16) DEFAULT 'none' NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"expired_at" timestamp with time zone,
	"payment_status" varchar(16) DEFAULT 'none' NOT NULL,
	"provider" varchar(24),
	"usage" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"feature_flags" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "subscription_user_id_unique" UNIQUE("user_id")
);
--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "subscription" ADD CONSTRAINT "subscription_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;

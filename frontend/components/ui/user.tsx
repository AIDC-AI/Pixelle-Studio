/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useApp } from "@/context"
import { UserRound } from "lucide-react"
import { Avatar, HoverCard } from "radix-ui"

const User = () => {
    const { user } = useApp()

    return (
        <HoverCard.Root>
			<HoverCard.Trigger asChild>
				<Avatar.Root className="flex items-center justify-center w-6 h-6 rounded-full bg-[#0078d4] p-1">
                    {/* <Avatar.Fallback className="text-gray-900 text-xs">{user?.username?.[0]}</Avatar.Fallback> */}
                    <UserRound className="text-white" />
                </Avatar.Root>
			</HoverCard.Trigger>

			<HoverCard.Portal>
				<HoverCard.Content 
                    className="flex flex-col gap-1 w-40 bg-[rgba(40,40,40,0.6)] backdrop-blur-sm rounded-md p-2 animate-up-fade will-change-[transform,opacity]"
                    sideOffset={5}
                >
                    <span
                        className="text-sm text-white truncate cursor-default"
                    >
						{user?.username}
					</span>
					<span
                        className="text-sm text-white truncate cursor-default"
                    >
						{user?.email}
					</span>
                    {/* <button
                        className="border border-gray-400 hover:border-gray-800 hover:bg-gray-100 text-xs text-gray-900 w-full rounded-sm px-2"
                        onClick={logout}
                    >
                        登出
                    </button> */}
				</HoverCard.Content>
			</HoverCard.Portal>
		</HoverCard.Root>
    )
}

export default User
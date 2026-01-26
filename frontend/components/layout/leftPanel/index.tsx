'use client'

import { useState } from 'react'
import { MessageSquare, Wrench } from 'lucide-react'
import CollaspeButton from '../../ui/collapseButton'
import TabButton from '../../ui/tabButton'
import ChatPanel from './chatPanel'
import SkillsPanel from './skillsPanel'
import { Session } from '@/types/session'
import User from '@/components/ui/user'

interface IProps {
  sessions?: Session[]
  handleNewSession?: (input: string) => void
  handleChangeSession?: (id: string) => void
  handleDeleteSession?: (id: string) => void
  isCollapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
}

export type TAB_TYPE = 'chat' | 'skills'

const TABS = [
  {
    title: '对话',
    type: 'chat',
    icon: <MessageSquare className="w-5 h-5" />
  },
  {
    title: '能力',
    type: 'skills',
    icon: <Wrench className="w-5 h-5" />
  }
]

const LeftPanel: React.FC<IProps> = (props) => {
  const { sessions, handleNewSession, handleChangeSession, handleDeleteSession, isCollapsed = false, onCollapsedChange } = props

  const [currentTab, setCurrentTab] = useState<TAB_TYPE>('chat')

  const handleCollapse = () => {
    onCollapsedChange?.(!isCollapsed)
  }

  const renderTabPanel = () => {
    switch (currentTab) {
      case 'chat':
        return <ChatPanel
          sessions={sessions}
          handleNewSession={handleNewSession}
          handleChangeSession={handleChangeSession}
          handleDeleteSession={handleDeleteSession}
        />
      case 'skills':
        return <SkillsPanel />
    }
  }

  if (isCollapsed) {
    return (
      <div className="w-12 bg-white border-r border-gray-200 flex flex-col items-center py-4 gap-4">
        <CollaspeButton
          isCollapsed={isCollapsed}
          onClick={handleCollapse}
        />
        {
          TABS?.map((tab) => <TabButton
            key={tab.title}
            isCollapsed={isCollapsed}
            isActive={currentTab === tab.type}
            onClick={() => setCurrentTab(tab.type as TAB_TYPE)}
          >
            {tab.icon}
          </TabButton>)
        }
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-row gap-2 items-center">
            <User />
            <h2 className="text-lg font-semibold text-gray-800">Pixelle-Studio</h2>
          </div>
          <CollaspeButton
            isCollapsed={isCollapsed}
            onClick={handleCollapse}
          />
        </div>

        {/* Tabs */}
        <div className="grid grid-cols-2 gap-2">
          {
            TABS?.map((tab, index) => <TabButton
              key={tab.title}
              isCollapsed={isCollapsed}
              isActive={currentTab === tab.type}
              onClick={() => setCurrentTab(tab.type as TAB_TYPE)}
              className={TABS.length % 2 !== 0 && index === TABS.length - 1 ? 'col-span-2' : ''}
            >
              {tab.icon}
              <span className="font-default">{tab.title}</span>
            </TabButton>)
          }
        </div>
      </div>
      {/* Content */}
      {
        renderTabPanel()
      }
    </div>
  )
}

export default LeftPanel;